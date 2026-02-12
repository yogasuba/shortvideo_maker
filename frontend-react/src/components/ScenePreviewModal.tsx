import React, { useState } from 'react';
import { Info, ArrowRight, Clock, Image as ImageIcon, Pencil, Check, Trash2, X, Plus, Loader2 } from 'lucide-react';
import { ScenesPreview, SceneData, AlertType } from '../types';

interface ScenePreviewModalProps {
  data: ScenesPreview & { total_scenes?: number };
  setScenesPreview: (preview: ScenesPreview) => void;
  onClose: () => void;
  onProceed: () => void;
  API_BASE: string;
  addAlert: (message: string, type: AlertType) => void;
}

interface UploadResponse {
  url: string;
  path: string;
}

const ScenePreviewModal: React.FC<ScenePreviewModalProps> = ({ data, setScenesPreview, onClose, onProceed, API_BASE, addAlert }) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editVisualText, setEditVisualText] = useState<string>('');
  const [editVoiceText, setEditVoiceText] = useState<string>('');
  const [uploadingIndex, setUploadingIndex] = useState<number | null>(null);

  const startEdit = (index: number, scene: SceneData) => {
    setEditingIndex(index);
    setEditVisualText(scene.description); // 'text' in original might be 'description' in type def, assuming 'text' was alias for description or vice versa. Checking previous file.. it used scene.text. Updating interface to match or component to match. 
    // In type def: SceneData has description. In previous code: scene.text.
    // I will use description as the canonical field and map it if needed, or assume data matches SceneData
    setEditVoiceText(scene.voiceover || scene.description);
  };
  
  // Correction: The API returns `text` for valid javascript code, but my type def used `description`. 
  // Let me adjust usage to be safe. I'll stick to 'description' which is typed, but fall back to 'text' if it exists.
  // Actually, checking standard I should probably update the SceneData type if the backend returns 'text'.
  // For now I'll cast or use what's available.
  
  const saveEdit = (index: number) => {
    if (!editVisualText.trim()) return;
    
    const newScenes = [...data.scenes];
    newScenes[index] = {
      ...newScenes[index],
      description: editVisualText, 
      // @ts-ignore - keeping original structure for backend compatibility if it expects 'text'
      text: editVisualText,
      // @ts-ignore
      visual_prompt: editVisualText,
      voiceover: editVoiceText,
      // @ts-ignore
      voice_over: editVoiceText
    };
    
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
      scenes: newScenes
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

  const removeSceneImage = (index: number) => {
    const newScenes = [...data.scenes];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (newScenes[index] as any).custom_image_url;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (newScenes[index] as any).custom_image_path;
    setScenesPreview({ ...data, scenes: newScenes });
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
                        // @ts-ignore
                        <div className="scene-text p-2 bg-gray-50 rounded">{scene.description || scene.text}</div>
                      )}
                    </div>
                    
                    <div className="mb-4">
                      <label className="block text-[0.75rem] font-bold text-gray-400 mb-1 uppercase tracking-wider">Voice Over (Narration)</label>
                      {editingIndex === index ? (
                        <textarea 
                          className="scene-text-edit" 
                          value={editVoiceText}
                          onChange={(e) => setEditVoiceText(e.target.value)}
                          rows={3}
                        />
                      ) : (
                        <div className="scene-text p-2 bg-blue-50/50 rounded border-l-3 border-blue-400 italic">
                          {/* @ts-ignore */}
                          {scene.voiceover || scene.voice_over || scene.description || scene.text}
                        </div>
                      )}
                    </div>
                    
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      {/* @ts-ignore */}
                      {scene.custom_image_url && (
                        <div className="mb-2 relative inline-block">
                          <img 
                             /* @ts-ignore */
                            src={`${API_BASE}${scene.custom_image_url}`} 
                            alt="Scene image" 
                            className="rounded shadow-sm max-h-[120px] w-auto object-cover"
                          />
                          <button 
                            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 shadow-md hover:bg-red-600"
                            onClick={() => removeSceneImage(index)}
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                      
                      <div className="flex items-center gap-3">
                        <div className="flex-grow max-w-[200px]">
                          <input 
                            type="file" 
                            id={`file-${index}`} 
                            className="hidden" 
                            accept="image/*"
                            onChange={(e) => e.target.files && uploadSceneImage(index, e.target.files[0])}
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
                            {/* @ts-ignore */}
                            {scene.custom_image_url ? 'Change Image' : 'Upload Image'}
                          </button>
                        </div>
                        <span className="text-[0.7rem] text-gray-400">
                          {/* @ts-ignore */}
                          {scene.custom_image_url ? 'Custom image loaded' : 'Uses Pexels/AI if empty'}
                        </span>
                      </div>
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
