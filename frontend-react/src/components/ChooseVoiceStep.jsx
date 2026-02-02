import React, { useState } from 'react';
import { Mic, Heart, User } from 'lucide-react';

const ChooseVoiceStep = ({ 
  config, selectedVoice, setSelectedVoice, 
  language, prevStep, nextStep, API_BASE 
}) => {
  
  const [loadingVoice, setLoadingVoice] = useState(null);

  const selectVoice = async (voiceId) => {
    setSelectedVoice(voiceId);
    setLoadingVoice(voiceId);
    
    try {
      const response = await fetch(`${API_BASE}/api/audio/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: "This is a preview of how your video will sound with this voice.",
          language: language,
          voice: voiceId
        })
      });
      const data = await response.json();
      if (data.success) {
        const audio = new Audio(`${API_BASE}${data.data.url}`);
        audio.oncanplaythrough = () => setLoadingVoice(null);
        audio.onended = () => setLoadingVoice(null);
        audio.onerror = () => setLoadingVoice(null);
        audio.play();
      } else {
        setLoadingVoice(null);
      }
    } catch (error) {
      console.error('Voice preview failed:', error);
      setLoadingVoice(null);
    }
  };

  return (
    <div className="card-custom">
      <div className="card-header-custom flex items-center">
        <Mic className="mr-2" />
        <h4 className="mb-0 text-xl font-semibold">Choose a Voice</h4>
      </div>
      <div className="card-body p-6">
        <p className="text-gray-500 mb-6">Select the perfect voice for your content</p>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {config?.voices?.map((voice) => (
            <div 
              key={voice.id}
              className={`voice-option relative ${selectedVoice === voice.id ? 'selected' : ''}`}
              onClick={() => selectVoice(voice.id)}
            >
              <div className="voice-icon">
                {loadingVoice === voice.id ? (
                  <span className="loading-spinner !border-primary border-t-transparent !mr-0 !w-8 !h-8" />
                ) : (
                  voice.gender === 'female' ? <Heart className="w-8 h-8" /> : <User className="w-8 h-8" />
                )}
              </div>
              <h6 className="mb-1 font-semibold">{voice.name}</h6>
              <small className="text-gray-500 capitalize">{voice.accent} • {voice.gender}</small>
            </div>
          ))}
        </div>
        
        <div className="flex justify-between mt-8">
          <button className="px-6 py-2 border-2 border-gray-200 rounded-lg text-gray-700 font-semibold hover:bg-gray-50" onClick={prevStep}>
            Previous
          </button>
          <button className="btn-primary-custom" onClick={nextStep}>
            Next: Image Style
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChooseVoiceStep;
