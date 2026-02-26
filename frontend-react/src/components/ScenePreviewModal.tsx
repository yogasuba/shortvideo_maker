import React, { useState } from 'react';
import { Info, ArrowRight, Clock, Image as ImageIcon, Pencil, Check, Trash2, X, Plus, Loader2, RotateCw, Type, AlignCenter, Eye, EyeOff, Settings2, Palette, Square, Bold, Mic, Pin } from 'lucide-react';
import { ScenesPreview, SceneData, AlertType } from '../types';

interface ScenePreviewModalProps {
  data: ScenesPreview;
  setScenesPreview: (preview: ScenesPreview) => void;
  onClose: () => void;
  onProceed: () => void;
  API_BASE: string;
  addAlert: (message: string, type: AlertType) => void;
  language: string;
  selectedVoice: string;
}

interface UploadResponse {
  url: string;
  path: string;
}

const ScenePreviewModal: React.FC<ScenePreviewModalProps> = ({ 
  data, 
  setScenesPreview, 
  onClose, 
  onProceed, 
  API_BASE, 
  addAlert, 
  language, 
  selectedVoice 
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editVisualText, setEditVisualText] = useState<string>('');
  const [editVoiceText, setEditVoiceText] = useState<string>('');
  const [uploadingIndex, setUploadingIndex] = useState<number | null>(null);
  const [uploadingAudioIndex, setUploadingAudioIndex] = useState<number | null>(null);
  const [isGeneratingVoice, setIsGeneratingVoice] = useState<number | null>(null);
  const [activeLineIndices, setActiveLineIndices] = useState<Record<number, number | null>>({});

  // Load persistent audio defaults on mount
  React.useEffect(() => {
    const introDefault = localStorage.getItem('app_default_intro_audio');
    const outroDefault = localStorage.getItem('app_default_outro_audio');
    
    if (introDefault || outroDefault) {
      const newScenes = [...data.scenes];
      let changed = false;
      
      if (introDefault && newScenes[0] && !newScenes[0].custom_audio_url) {
        try {
          const audioData = JSON.parse(introDefault);
          newScenes[0] = {
            ...newScenes[0],
            custom_audio_url: audioData.url,
            custom_audio_path: audioData.path,
            duration: audioData.duration,
            duration_is_auto: false,
            is_default: true
          };
          changed = true;
        } catch (e) { console.error('Error parsing intro default', e); }
      }
      
      const lastIdx = newScenes.length - 1;
      if (outroDefault && lastIdx > 0 && !newScenes[lastIdx].custom_audio_url) {
        try {
          const audioData = JSON.parse(outroDefault);
          newScenes[lastIdx] = {
            ...newScenes[lastIdx],
            custom_audio_url: audioData.url,
            custom_audio_path: audioData.path,
            duration: audioData.duration,
            duration_is_auto: false,
            is_default: true
          };
          changed = true;
        } catch (e) { console.error('Error parsing outro default', e); }
      }
      
      if (changed) {
        setScenesPreview({ ...data, scenes: newScenes });
      }
    }
  }, []); // Only on mount

  const startEdit = (index: number, scene: SceneData) => {
    setEditingIndex(index);
    setEditVisualText(scene.description); // 'text' in original might be 'description' in type def, assuming 'text' was alias for description or vice versa. Checking previous file.. it used scene.text. Updating interface to match or component to match. 
    // In type def: SceneData has description. In previous code: scene.text.
    // I will use description as the canonical field and map it if needed, or assume data matches SceneData
    setEditVoiceText(scene.voiceover || scene.description);
  };

  const getCurrentVal = (index: number, field: keyof SceneData) => {
    const activeLineIndex = activeLineIndices[index];
    const scene = data.scenes[index];
    if (activeLineIndex !== undefined && activeLineIndex !== null && scene.line_styles?.[activeLineIndex]) {
      // For boolean fields like bg_visible, handle explicitly
      if (scene.line_styles[activeLineIndex][field] !== undefined) {
        return scene.line_styles[activeLineIndex][field];
      }
    }
    // @ts-ignore - field might not exist on scene directly but we're handling optional fields
    return scene[field];
  };

  const saveEdit = (index: number) => {
    if (!editVisualText.trim()) return;
    
    const newScenes = [...data.scenes];
    const currentScene = newScenes[index];
    
    // Recalculate duration if it's currently on "auto"
    let newDuration = currentScene.duration;
    if (currentScene.duration_is_auto !== false) {
      const textToAnalyze = editVoiceText || editVisualText;
      const wordCount = textToAnalyze.trim().split(/\s+/).length;
      // Use 2.5 wps (same as backend), clamp between 3 and 12 seconds
      newDuration = Math.max(3, Math.min(Math.ceil(wordCount / 2.5), 12));
    }

    const isTextChanged = currentScene.voice_over !== editVoiceText || currentScene.text !== editVisualText;

    newScenes[index] = {
      ...currentScene,
      description: editVisualText, 
      text: editVisualText,
      visual_prompt: editVisualText,
      voiceover: editVoiceText,
      voice_over: editVoiceText,
      duration: newDuration,
      duration_is_auto: currentScene.duration_is_auto !== false
    };

    // If text changed, the old audio (including system defaults) is no longer valid
    if (isTextChanged) {
      delete newScenes[index].custom_audio_url;
      delete newScenes[index].custom_audio_path;
      delete newScenes[index].is_default;
      delete newScenes[index].is_system_default;
      
      // Reset duration to auto if audio was cleared
      newScenes[index].duration_is_auto = true;
      const textToAnalyze = editVoiceText || editVisualText;
      const wordCount = textToAnalyze.trim().split(/\s+/).length;
      newScenes[index].duration = Math.max(3, Math.min(Math.ceil(wordCount / 2.5), 12));
    }
    
    setScenesPreview({ ...data, scenes: newScenes });
    setEditingIndex(null);
  };

  const deleteScene = (index: number) => {
    if (!window.confirm('Are you sure you want to delete this scene?')) return;
    
    const newScenes = data.scenes.filter((_, i) => i !== index).map((scene, i) => ({
      ...scene,
      scene_number: i + 1
    }));
    
    setScenesPreview({ 
      ...data, 
      scenes: newScenes,
      total_scenes: newScenes.length
    });
  };

  const uploadSceneImage = async (index: number, file: File) => {
    if (!file) return;
    
    setUploadingIndex(index);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${API_BASE}/api/upload/scene-image`, {
        method: 'POST',
        body: formData
      });
      const resData = await response.json();
      
      if (resData.success) {
        const newScenes = [...data.scenes];
        const uploadData = resData.data as UploadResponse;
        
        // Use type intersection or extension for custom fields not in basic SceneData
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (newScenes[index] as any).custom_image_url = uploadData.url;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (newScenes[index] as any).custom_image_path = uploadData.path;
        
        setScenesPreview({ ...data, scenes: newScenes });
        addAlert(`Image uploaded for scene ${index + 1}`, 'success');
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      addAlert('Failed to upload image', 'error');
    } finally {
      setUploadingIndex(null);
    }
  };

  const uploadSceneAudio = async (index: number, file: File) => {
    if (!file) return;
    
    setUploadingAudioIndex(index);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${API_BASE}/api/upload/scene-audio`, {
        method: 'POST',
        body: formData
      });
      const resData = await response.json();
      
      if (resData.success) {
        const newScenes = [...data.scenes];
        newScenes[index] = {
          ...newScenes[index],
          custom_audio_url: resData.data.url,
          custom_audio_path: resData.data.path,
          duration: resData.data.duration,
          duration_is_auto: false
        };
        setScenesPreview({ ...data, scenes: newScenes });
        addAlert(`Audio uploaded for scene ${index + 1}`, 'success');
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Audio upload error:', error);
      addAlert('Failed to upload audio', 'error');
     } finally {
       setUploadingAudioIndex(null);
     }
   };
 
  const pinAsDefault = async (index: number) => {
    const scene = data.scenes[index];
    if (!scene.custom_audio_url || !scene.custom_audio_path) {
      addAlert("Generate or upload audio first before pinning", "warning");
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/audio/set-default`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: scene.custom_audio_path,
          type: index === 0 ? 'intro' : 'outro',
          text: scene.voice_over || scene.text // Send text for validation
        })
      });
      
      const resData = await response.json();
      if (resData.success) {
        // Save to local storage too for immediate local consistency
        const key = index === 0 ? 'app_default_intro_audio' : 'app_default_outro_audio';
        localStorage.setItem(key, JSON.stringify({
          url: scene.custom_audio_url,
          path: scene.custom_audio_path,
          duration: scene.duration
        }));
        
        const newScenes = [...data.scenes];
        newScenes[index] = { ...newScenes[index], is_default: true, is_system_default: true };
        setScenesPreview({ ...data, scenes: newScenes });
        
        addAlert(`${index === 0 ? 'Intro' : 'Outro'} saved as SYSTEM DEFAULT!`, 'success');
      } else {
        throw new Error(resData.detail || 'Failed to save system default');
      }
    } catch (error) {
      console.error('Pin error:', error);
      addAlert(`Error: ${(error as Error).message}`, 'error');
    }
  };

  const generateAIVoice = async (index: number) => {
    const scene = data.scenes[index];
    const text = scene.voice_over || scene.text;
    
    if (!text) {
      addAlert("Scene has no text to narrate", "warning");
      return;
    }
    
    setIsGeneratingVoice(index);
    try {
      const response = await fetch(`${API_BASE}/api/audio/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          language: language || 'en',
          voice: selectedVoice
        })
      });
      
      const resData = await response.json();
      if (resData.success) {
        const newScenes = [...data.scenes];
        newScenes[index] = {
          ...newScenes[index],
          custom_audio_url: resData.data.url,
          custom_audio_path: resData.data.path, 
          duration: resData.data.duration || scene.duration,
          duration_is_auto: false
        };
        setScenesPreview({ ...data, scenes: newScenes });
        addAlert(`AI Voice generated for Scene ${index + 1}`, 'success');
      } else {
        throw new Error(resData.detail || 'Failed to generate voice');
      }
    } catch (error) {
      console.error('Audio generation error:', error);
      addAlert(`Generation failed: ${(error as Error).message}`, 'error');
    } finally {
      setIsGeneratingVoice(null);
    }
  };

  const removeSceneAudio = (index: number) => {
    const newScenes = [...data.scenes];
    const scene = { ...newScenes[index] };
    delete scene.custom_audio_url;
    delete scene.custom_audio_path;
    delete scene.is_default;
    delete scene.is_system_default;
    
    // Recalculate duration
    const textToAnalyze = scene.voice_over || scene.text;
    if (textToAnalyze) {
      const wordCount = textToAnalyze.trim().split(/\s+/).length;
      scene.duration = Math.max(3, Math.min(Math.ceil(wordCount / 2.5), 12));
    }
    scene.duration_is_auto = true;
    
    newScenes[index] = scene;
    setScenesPreview({ ...data, scenes: newScenes });
  };

  const removeSceneImage = (index: number) => {
    const newScenes = [...data.scenes];
    delete newScenes[index].custom_image_url;
    delete newScenes[index].custom_image_path;
    setScenesPreview({ ...data, scenes: newScenes });
  };

  const updateSceneConfig = (index: number, updates: Partial<SceneData>) => {
    const newScenes = [...data.scenes];
    const activeLineIndex = activeLineIndices[index];

    if (activeLineIndex !== undefined && activeLineIndex !== null) {
      const scene = { ...newScenes[index] };
      const lines = (scene.text || '').split('\n');
      const lineStyles = [...(scene.line_styles || [])];
      
      // Ensure the lineStyles array is the correct length
      while (lineStyles.length < lines.length) {
        lineStyles.push({});
      }
      
      lineStyles[activeLineIndex] = { ...lineStyles[activeLineIndex], ...updates };
      scene.line_styles = lineStyles;
      newScenes[index] = scene;
    } else {
      newScenes[index] = { ...newScenes[index], ...updates };
    }
    setScenesPreview({ ...data, scenes: newScenes });
  };

  const rotateScene = (index: number) => {
    const currentRotation = data.scenes[index].rotation || 0;
    const nextRotation = (currentRotation + 90) % 360;
    updateSceneConfig(index, { rotation: nextRotation });
  };

  return (
    <div className="fixed inset-0 z-[1050] flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-[15px] w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        <div className="p-4 border-b flex justify-between items-center">
          <h5 className="text-xl font-bold">Scene Split Preview</h5>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-6 h-6" />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto flex-grow">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
            <div>
              <p className="text-gray-500">Your script will be split into <strong className="text-primary">{data.total_scenes || data.scenes.length} scenes</strong>.</p>
            </div>
            <button className="btn-primary-custom flex items-center" onClick={onProceed}>
              Choose Voice <ArrowRight className="ml-2 w-5 h-5" />
            </button>
          </div>
          
          <div className="bg-blue-50 text-blue-800 p-4 rounded-lg flex items-center mb-6">
            <Info className="mr-2 w-5 h-5 flex-shrink-0" />
            <span className="text-sm">Each scene will become a separate visual with its own audio narration.</span>
          </div>
          
          <h6 className="font-bold mb-4">Scene Breakdown:</h6>
          
          <div className="space-y-4">
            {data.scenes.map((scene, index) => (
              <div key={index} className="scene-preview-card">
                <div className="flex items-start">
                  <div className="scene-number flex-shrink-0">{scene.scene_number}</div>
                  <div className="flex-grow min-w-0">
                    <div className="mb-4">
                      <label className="block text-[0.75rem] font-bold text-gray-400 mb-1 uppercase tracking-wider">Visual Prompt (Scene Description)</label>
                      {editingIndex === index ? (
                        <textarea 
                          className="scene-text-edit" 
                          value={editVisualText}
                          onChange={(e) => setEditVisualText(e.target.value)}
                          rows={3}
                        />
                      ) : (
                        <div className="flex flex-col gap-1">
                          {(scene.text || '').split('\n').map((line, lIdx) => {
                            const lineStyle = (scene.line_styles && scene.line_styles[lIdx]) || {};
                            const isActive = activeLineIndices[index] === lIdx;
                            return (
                              <div 
                                key={lIdx}
                                className={`scene-text p-2 rounded cursor-pointer transition-all duration-200 ${isActive ? 'ring-2 ring-primary border-transparent' : 'bg-gray-50 border-transparent hover:bg-gray-100'}`}
                                onClick={() => setActiveLineIndices(prev => ({ 
                                  ...prev, 
                                  [index]: isActive ? null : lIdx 
                                }))}
                                style={{ 
                                  color: lineStyle.subtitle_color || scene.subtitle_color || 'inherit', 
                                  fontWeight: (lineStyle.subtitle_bold !== undefined ? lineStyle.subtitle_bold : scene.subtitle_bold) ? 'bold' : 'normal',
                                  borderLeft: (lineStyle.subtitle_bold !== undefined ? lineStyle.subtitle_bold : scene.subtitle_bold) ? `2px solid ${lineStyle.subtitle_color || scene.subtitle_color || '#ccc'}` : 'none'
                                }}
                              >
                                {line || <span className="text-gray-300 italic">Empty line</span>}
                              </div>
                            );
                          })}
                          <button 
                            className="text-[0.6rem] text-primary font-bold uppercase mt-1 self-start hover:underline px-1 py-0.5"
                            onClick={() => setActiveLineIndices(prev => ({ ...prev, [index]: null }))}
                          >
                            {activeLineIndices[index] !== null && activeLineIndices[index] !== undefined ? (
                               <span className="flex items-center gap-1"><X className="w-2.5 h-2.5" /> Back to All Lines</span>
                            ) : null}
                          </button>
                        </div>
                      )}
                    </div>
                    
                    <div className={`mb-4 transition-all duration-300 ${scene.show_image_only ? 'opacity-30' : 'opacity-100'}`}>
                      <label className="block text-[0.75rem] font-bold text-gray-400 mb-1 uppercase tracking-wider">Voice Over (Narration)</label>
                      {editingIndex === index ? (
                        <textarea 
                          className="scene-text-edit" 
                          value={editVoiceText}
                          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setEditVoiceText(e.target.value)}
                          rows={3}
                          disabled={scene.show_image_only}
                        />
                      ) : (
                        <div className="scene-text p-2 bg-blue-50/50 rounded border-l-3 border-blue-400 italic whitespace-pre-wrap">
                          {/* @ts-ignore */}
                          {scene.voiceover || scene.voice_over || scene.description || scene.text}
                        </div>
                      )}
                    </div>

                    {/* Enhanced Controls */}
                    <div className="bg-gray-50/80 p-3 rounded-lg border border-gray-100 mb-4">
                      <div className="flex items-center gap-2 mb-3 text-primary text-[0.75rem] font-bold uppercase tracking-wider">
                        <Settings2 className="w-3 h-3" /> Scene Settings
                      </div>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {/* Subtitle Controls */}
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[0.75rem] font-medium text-gray-600 flex items-center gap-1">
                              <AlignCenter className="w-3 h-3" /> Position
                            </span>
                            <div className="flex bg-gray-200 p-0.5 rounded-md">
                              <button 
                                className={`px-2 py-0.5 text-[0.7rem] rounded ${(!scene.subtitle_position || scene.subtitle_position === 'bottom') ? 'bg-white shadow-sm font-bold' : ''}`}
                                onClick={() => updateSceneConfig(index, { subtitle_position: 'bottom' })}
                                disabled={scene.show_image_only}
                              >
                                Bottom
                              </button>
                              <button 
                                className={`px-2 py-0.5 text-[0.7rem] rounded ${scene.subtitle_position === 'center' ? 'bg-white shadow-sm font-bold' : ''}`}
                                onClick={() => updateSceneConfig(index, { subtitle_position: 'center' })}
                                disabled={scene.show_image_only}
                              >
                                Center
                              </button>
                            </div>
                          </div>

                           <div className="flex items-center justify-between">
                            <span className="text-[0.75rem] font-medium text-gray-600 flex items-center gap-1">
                              <Type className="w-3 h-3" /> Text Size
                            </span>
                            <div className="flex items-center gap-2">
                              <input 
                                type="range" 
                                min="20" 
                                max="120" 
                                value={getCurrentVal(index, 'subtitle_size') || 60}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateSceneConfig(index, { subtitle_size: parseInt(e.target.value) })}
                                className="w-20 accent-primary"
                                disabled={scene.show_image_only}
                              />
                              <span className="text-[0.7rem] font-bold text-primary w-6">{getCurrentVal(index, 'subtitle_size') || 60}</span>
                            </div>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-[0.75rem] font-medium text-gray-600 flex items-center gap-1">
                              <Square className={`w-3 h-3 ${getCurrentVal(index, 'subtitle_bg_visible') !== false ? 'fill-gray-400' : ''}`} /> BG Box
                            </span>
                            <button 
                              className={`px-3 py-1 text-[0.7rem] rounded font-bold transition-colors ${getCurrentVal(index, 'subtitle_bg_visible') !== false ? 'bg-primary text-white' : 'bg-gray-200 text-gray-500'}`}
                              onClick={() => updateSceneConfig(index, { subtitle_bg_visible: getCurrentVal(index, 'subtitle_bg_visible') === false })}
                              disabled={scene.show_image_only}
                            >
                              {getCurrentVal(index, 'subtitle_bg_visible') !== false ? 'ON' : 'OFF'}
                            </button>
                          </div>
                        </div>

                        {/* General Controls */}
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[0.75rem] font-medium text-gray-600 flex items-center gap-1">
                              <Palette className="w-3 h-3" /> Color
                            </span>
                            <div className="flex gap-1.5 Items-center">
                              {[
                                { name: 'White', color: '#FFFFFF' },
                                { name: 'Yellow', color: '#FFFF00' },
                                { name: 'Cyan', color: '#00FFFF' },
                                { name: 'Green', color: '#00FF00' },
                                { name: 'Red', color: '#FF0000' },
                                { name: 'Orange', color: '#FFA500' },
                                { name: 'Blue', color: '#0000FF' },
                                { name: 'Pink', color: '#FFC0CB' },
                                { name: 'Purple', color: '#800080' },
                                { name: 'Black', color: '#000000' }
                              ].map((c) => (
                                <button
                                  key={c.name}
                                  className={`w-4 h-4 rounded-full border border-gray-300 transition-transform ${ (getCurrentVal(index, 'subtitle_color') || 'white').toLowerCase() === c.name.toLowerCase() ? 'scale-125 ring-2 ring-primary ring-offset-1' : 'hover:scale-110'}`}
                                  style={{ backgroundColor: c.color }}
                                  onClick={() => updateSceneConfig(index, { subtitle_color: c.name.toLowerCase() })}
                                  title={c.name}
                                  disabled={scene.show_image_only}
                                />
                              ))}
                            </div>
                          </div>

                           <div className="flex items-center justify-between">
                            <span className="text-[0.75rem] font-medium text-gray-600 flex items-center gap-1">
                              <Type className="w-3 h-3" /> Style
                            </span>
                            <button 
                              className={`flex items-center gap-1 px-2 py-1 rounded text-[0.7rem] font-bold transition-colors ${getCurrentVal(index, 'subtitle_bold') ? 'bg-primary/10 text-primary' : 'bg-gray-100 text-gray-400'}`}
                              onClick={() => updateSceneConfig(index, { subtitle_bold: !getCurrentVal(index, 'subtitle_bold') })}
                            >
                              <Bold className="w-3 h-3" /> Bold
                            </button>
                            <button 
                              className={`flex items-center gap-1 px-2 py-1 rounded text-[0.7rem] font-bold transition-colors ${scene.show_image_only ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}
                              onClick={() => updateSceneConfig(index, { show_image_only: !scene.show_image_only })}
                            >
                              {scene.show_image_only ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                              {scene.show_image_only ? 'Image Only' : 'Normal'}
                            </button>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-[0.75rem] font-medium text-gray-600 flex items-center gap-1">
                              <Clock className="w-3 h-3" /> Duration
                            </span>
                            <div className="flex items-center gap-1">
                              <input 
                                type="number" 
                                value={scene.duration}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateSceneConfig(index, { duration: parseFloat(e.target.value) || 1, duration_is_auto: false })}
                                className="w-12 p-0.5 text-[0.75rem] border rounded text-center font-bold"
                                min="1"
                                max="30"
                                step="0.5"
                              />
                              <span className="text-[0.7rem] text-gray-400">sec</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <div className="flex items-start gap-4">
                        {scene.custom_image_url && (
                          <div className="relative inline-block group">
                            <img 
                              src={scene.custom_image_url.startsWith('http') ? scene.custom_image_url : `${API_BASE}${scene.custom_image_url}`} 
                              alt="Scene image" 
                              className="rounded shadow-sm max-h-[140px] w-auto object-cover transition-transform duration-300"
                              style={{ transform: `rotate(${scene.rotation || 0}deg)` }}
                            />
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded">
                               <button 
                                 className="p-2 bg-white/20 hover:bg-white/40 text-white rounded-full transition-colors"
                                 onClick={() => rotateScene(index)}
                                 title="Rotate Image"
                               >
                                 <RotateCw className="w-4 h-4" />
                               </button>
                            </div>
                            <button 
                              className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 shadow-md hover:bg-red-600"
                              onClick={() => removeSceneImage(index)}
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        )}
                        
                        {!scene.custom_image_url && (
                          <div 
                            className="w-32 h-20 bg-gray-100 rounded border-2 border-dashed border-gray-200 flex flex-col items-center justify-center text-gray-400 hover:bg-gray-200 transition-colors cursor-pointer overflow-hidden"
                            onClick={() => document.getElementById(`file-${index}`)?.click()}
                          >
                            <ImageIcon className="w-6 h-6 mb-1" style={{ transform: `rotate(${scene.rotation || 0}deg)` }} />
                            <span className="text-[0.6rem] font-bold uppercase">No Image</span>
                            <button 
                              className="absolute p-1 bg-primary text-white rounded-full -bottom-1 -right-1 shadow-sm"
                              onClick={(e: React.MouseEvent) => { e.stopPropagation(); rotateScene(index); }}
                            >
                              <RotateCw className="w-2 h-2" />
                            </button>
                          </div>
                        )}

                        <div className="flex-grow">
                          <div className="flex items-center gap-3">
                            <div className="flex-grow max-w-[200px]">
                              <input 
                                type="file" 
                                id={`file-${index}`} 
                                className="hidden" 
                                accept="image/*"
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                  if (e.target.files && e.target.files[0]) {
                                    uploadSceneImage(index, e.target.files[0]);
                                  }
                                }}
                              />
                              <button 
                                className="w-full px-4 py-2 text-sm border-2 border-gray-200 rounded-lg text-gray-600 font-semibold flex items-center justify-center hover:bg-gray-50 transition-colors"
                                onClick={() => document.getElementById(`file-${index}`)?.click()}
                                disabled={uploadingIndex === index}
                              >
                                {uploadingIndex === index ? (
                                  <Loader2 className="animate-spin w-4 h-4 mr-2" />
                                ) : (
                                  <Plus className="w-4 h-4 mr-2" />
                                )}
                                {scene.custom_image_url ? 'Change Image' : 'Upload Image'}
                              </button>
                            </div>
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                             <button 
                               className="flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-[0.7rem] font-bold text-gray-600 transition-colors"
                               onClick={() => rotateScene(index)}
                             >
                               <RotateCw className="w-3 h-3" /> Rotate {scene.rotation || 0}°
                             </button>
                             <span className="text-[0.7rem] text-gray-400">
                               {scene.custom_image_url ? 'Custom image loaded' : 'Uses Pexels/AI if empty'}
                             </span>
                          </div>
                        </div>
                      </div>

                       {(index === 0 || index === data.scenes.length - 1) && (
                        <div className="mt-3 p-3 bg-blue-50/50 rounded-lg border border-blue-100/50">
                          <div className="flex items-center justify-between mb-2">
                             <span className="text-[0.75rem] font-bold text-blue-700 flex items-center gap-1.5">
                               <Mic className="w-3.5 h-3.5" /> 
                               {index === 0 ? 'INTRO VOICE' : 'OUTRO VOICE'} (Custom)
                             </span>
                            <div className="flex items-center gap-2">
                              {scene.is_system_default && (
                                <span className="text-[0.6rem] font-bold bg-green-100 text-green-700 px-1.5 py-0.5 rounded flex items-center gap-1">
                                  <Check className="w-2.5 h-2.5" /> SYSTEM DEFAULT
                                </span>
                              )}
                              {scene.custom_audio_url && (
                                <button 
                                  onClick={() => pinAsDefault(index)}
                                  className={`p-1 rounded transition-colors ${scene.is_default || scene.is_system_default ? 'text-primary bg-primary/10' : 'text-gray-400 hover:text-primary'}`}
                                  title="Save as system default for all future videos"
                                >
                                  <Pin className={`w-3.5 h-3.5 ${scene.is_default || scene.is_system_default ? 'fill-current' : ''}`} />
                                </button>
                              )}
                              {scene.custom_audio_url && (
                                <button 
                                  onClick={() => removeSceneAudio(index)}
                                  className="text-red-500 hover:text-red-700 transition-colors"
                                  title="Remove Audio"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                           </div>
                          
                          <div className="flex flex-col gap-2">
                            {scene.custom_audio_url ? (
                              <div className="flex items-center gap-2">
                                <audio 
                                  src={scene.custom_audio_url.startsWith('http') ? scene.custom_audio_url : `${API_BASE}${scene.custom_audio_url}`} 
                                  key={scene.custom_audio_url}
                                  controls 
                                  className="h-8 flex-grow"
                                />
                                <span className="text-[0.7rem] font-bold text-blue-600 bg-blue-100 px-2 py-1 rounded">
                                  {scene.duration.toFixed(1)}s
                                </span>
                              </div>
                            ) : (
                              <div className="grid grid-cols-2 gap-2">
                                <button 
                                  className="flex items-center justify-center gap-2 px-3 py-1.5 bg-primary text-white rounded text-[0.65rem] font-bold hover:bg-primary/95 transition-colors disabled:opacity-50"
                                  onClick={() => generateAIVoice(index)}
                                  disabled={isGeneratingVoice === index}
                                >
                                  {isGeneratingVoice === index ? (
                                    <Loader2 className="animate-spin w-3 h-3" />
                                  ) : (
                                    <RotateCw className="w-3 h-3" />
                                  )}
                                  Generate AI Voice
                                </button>
                                
                                <div className="relative">
                                  <input 
                                    type="file" 
                                    id={`audio-file-${index}`} 
                                    className="hidden" 
                                    accept="audio/*"
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                      if (e.target.files && e.target.files[0]) {
                                        uploadSceneAudio(index, e.target.files[0]);
                                      }
                                    }}
                                  />
                                  <button 
                                    className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-white border border-blue-200 rounded text-blue-600 text-[0.65rem] font-bold hover:bg-blue-50 transition-colors"
                                    onClick={() => document.getElementById(`audio-file-${index}`)?.click()}
                                    disabled={uploadingAudioIndex === index}
                                  >
                                    {uploadingAudioIndex === index ? (
                                      <Loader2 className="animate-spin w-3 h-3" />
                                    ) : (
                                      <Plus className="w-3 h-3" />
                                    )}
                                    Upload Custom
                                  </button>
                                </div>
                              </div>
                            )}
                            <p className="text-[0.65rem] text-blue-400 font-medium">
                              {scene.custom_audio_url 
                                ? "✓ Voice loaded. Click Pin (stable icon) to save as server default." 
                                : `Generate AI voice for this scene once, then Pin it to save credits forever.`}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center mt-3 text-[0.75rem] text-gray-400">
                      {/* @ts-ignore */}
                      <Clock className="w-3 h-3 mr-1" /> {scene.duration || '0'}s
                    </div>
                  </div>
                  
                  <div className="flex flex-col gap-2 ml-4">
                    {editingIndex === index ? (
                      <button 
                        className="p-2 bg-green-500 text-white rounded-lg shadow-sm hover:bg-green-600"
                        onClick={() => saveEdit(index)}
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    ) : (
                      <button 
                        className="p-2 border-2 border-primary/20 text-primary rounded-lg hover:bg-primary/5"
                        onClick={() => startEdit(index, scene)}
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                    )}
                    <button 
                      className="p-2 border-2 border-red-100 text-red-400 rounded-lg hover:bg-red-50"
                      onClick={() => deleteScene(index)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="p-4 border-t flex justify-end gap-3 bg-gray-50">
          <button className="px-6 py-2 bg-white border-2 border-gray-200 rounded-lg font-bold" onClick={onClose}>
            Close
          </button>
          <button className="btn-primary-custom" onClick={onProceed}>
            Choose Voice <ArrowRight className="ml-2 w-5 h-5 inline" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ScenePreviewModal;
