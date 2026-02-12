import React, { useState } from 'react';
import { Info, ArrowRight, Clock, Image as ImageIcon, Pencil, Check, Trash2, X, Plus, Loader2, RotateCw, Type, AlignCenter, Eye, EyeOff, Settings2 } from 'lucide-react';

const ScenePreviewModal = ({ data, setScenesPreview, onClose, onProceed, API_BASE, addAlert }) => {
  const [editingIndex, setEditingIndex] = useState(null);
  const [editVisualText, setEditVisualText] = useState('');
  const [editVoiceText, setEditVoiceText] = useState('');
  const [uploadingIndex, setUploadingIndex] = useState(null);

  const startEdit = (index, scene) => {
    setEditingIndex(index);
    setEditVisualText(scene.text);
    setEditVoiceText(scene.voice_over || scene.text);
  };

  const saveEdit = (index) => {
    if (!editVisualText.trim()) return;
    
    const newScenes = [...data.scenes];
    newScenes[index] = {
      ...newScenes[index],
      text: editVisualText,
      visual_prompt: editVisualText,
      voice_over: editVoiceText
    };
    
    setScenesPreview({ ...data, scenes: newScenes });
    setEditingIndex(null);
  };

  const deleteScene = (index) => {
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

  const uploadSceneImage = async (index, file) => {
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
        newScenes[index] = {
          ...newScenes[index],
          custom_image_url: resData.data.url,
          custom_image_path: resData.data.path
        };
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

  const removeSceneImage = (index) => {
    const newScenes = [...data.scenes];
    delete newScenes[index].custom_image_url;
    delete newScenes[index].custom_image_path;
    setScenesPreview({ ...data, scenes: newScenes });
  };

  const updateSceneConfig = (index, updates) => {
    const newScenes = [...data.scenes];
    newScenes[index] = { ...newScenes[index], ...updates };
    setScenesPreview({ ...data, scenes: newScenes });
  };

  const rotateScene = (index) => {
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
              <p className="text-gray-500">Your script will be split into <strong className="text-primary">{data.total_scenes} scenes</strong>.</p>
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
                        <div className="scene-text p-2 bg-gray-50 rounded">{scene.text}</div>
                      )}
                    </div>
                    
                    <div className={`mb-4 transition-all duration-300 ${scene.show_image_only ? 'opacity-30' : 'opacity-100'}`}>
                      <label className="block text-[0.75rem] font-bold text-gray-400 mb-1 uppercase tracking-wider">Voice Over (Narration)</label>
                      {editingIndex === index ? (
                        <textarea 
                          className="scene-text-edit" 
                          value={editVoiceText}
                          onChange={(e) => setEditVoiceText(e.target.value)}
                          rows={3}
                          disabled={scene.show_image_only}
                        />
                      ) : (
                        <div className="scene-text p-2 bg-blue-50/50 rounded border-l-3 border-blue-400 italic">
                          {scene.voice_over || scene.text}
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
                                value={scene.subtitle_size || 60}
                                onChange={(e) => updateSceneConfig(index, { subtitle_size: parseInt(e.target.value) })}
                                className="w-20 accent-primary"
                                disabled={scene.show_image_only}
                              />
                              <span className="text-[0.7rem] font-bold text-primary w-6">{scene.subtitle_size || 60}</span>
                            </div>
                          </div>
                        </div>

                        {/* General Controls */}
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[0.75rem] font-medium text-gray-600 flex items-center gap-1">
                              <Eye className="w-3 h-3" /> Visibility
                            </span>
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
                                onChange={(e) => updateSceneConfig(index, { duration: parseFloat(e.target.value) || 1, duration_is_auto: false })}
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
                              src={`${API_BASE}${scene.custom_image_url}`} 
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
                            onClick={() => document.getElementById(`file-${index}`).click()}
                          >
                            <ImageIcon className="w-6 h-6 mb-1" style={{ transform: `rotate(${scene.rotation || 0}deg)` }} />
                            <span className="text-[0.6rem] font-bold uppercase">No Image</span>
                            <button 
                              className="absolute p-1 bg-primary text-white rounded-full -bottom-1 -right-1 shadow-sm"
                              onClick={(e) => { e.stopPropagation(); rotateScene(index); }}
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
                                onChange={(e) => uploadSceneImage(index, e.target.files[0])}
                              />
                              <button 
                                className="w-full px-4 py-2 text-sm border-2 border-gray-200 rounded-lg text-gray-600 font-semibold flex items-center justify-center hover:bg-gray-50 transition-colors"
                                onClick={() => document.getElementById(`file-${index}`).click()}
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
                    </div>

                    <div className="flex items-center mt-3 text-[0.75rem] text-gray-400">
                      <Clock className="w-3 h-3 mr-1" /> {scene.duration}s
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
