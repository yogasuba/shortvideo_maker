import React from 'react';
import { Settings, Smartphone, Monitor } from 'lucide-react';

const VideoDetailsStep = ({ 
  videoTitle, setVideoTitle, 
  language, setLanguage, 
  tone, setTone, 
  scenesCount, setScenesCount, 
  orientation, setOrientation, 
  subtitleStyle, setSubtitleStyle,
  nextStep, config 
}) => {
  
  const titleCount = videoTitle.length;
  
  return (
    <div className="card-custom">
      <div className="card-header-custom flex items-center">
        <Settings className="mr-2" />
        <h4 className="mb-0 text-xl font-semibold">Video Details</h4>
      </div>
      <div className="card-body p-6">
        <div className="mb-6">
          <label className="block mb-2 font-bold text-gray-700">Video Title *</label>
          <input 
            type="text" 
            className="form-control-custom" 
            value={videoTitle}
            onChange={(e) => setVideoTitle(e.target.value)}
            placeholder="Enter a title for your video" 
            maxLength={100}
          />
          <div className={`character-count ${titleCount > 90 ? (titleCount > 100 ? 'error' : 'warning') : ''}`}>
            {titleCount}/100
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block mb-2 font-bold text-gray-700">Output Language</label>
            <select 
              className="form-control-custom appearance-none bg-no-repeat bg-[right_1rem_center] bg-[length:1em_1em]"
              style={{ backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23343a40' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m2 5 6 6 6-6'/%3e%3c/svg%3e")` }}
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {config?.languages?.map((lang) => (
                <option key={lang} value={lang}>
                  {getLanguageName(lang)}
                </option>
              )) || (
                <>
                  <option value="en">English</option>
                  <option value="ta">Tamil</option>
                </>
              )}
            </select>
          </div>
          <div>
            <label className="block mb-2 font-bold text-gray-700">Tone</label>
            <select 
              className="form-control-custom appearance-none bg-no-repeat bg-[right_1rem_center] bg-[length:1em_1em]"
              style={{ backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23343a40' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m2 5 6 6 6-6'/%3e%3c/svg%3e")` }}
              value={tone}
              onChange={(e) => setTone(e.target.value)}
            >
              <option value="neutral">Neutral</option>
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="humorous">Humorous</option>
              <option value="educational">Educational</option>
              <option value="motivational">Motivational</option>
            </select>
          </div>
        </div>
        
        <div className="mb-8">
          <label className="block mb-2 font-bold text-gray-700">Number of Scenes (4-16)</label>
          <div className="flex items-center mb-1">
            <span className="mr-4 text-xl font-bold text-primary">{scenesCount}</span>
            <input 
              type="range" 
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary" 
              min="4" max="16" 
              value={scenesCount}
              onChange={(e) => setScenesCount(parseInt(e.target.value))}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 px-1">
            <span>4 (Short)</span>
            <span>8 (Standard)</span>
            <span>16 (Detailed)</span>
          </div>
        </div>

        <div className="mb-6">
          <label className="block mb-2 font-bold text-gray-700">Video Orientation</label>
          <div className="grid grid-cols-2 gap-4">
            <div 
              className={`orientation-option ${orientation === 'portrait' ? 'selected' : ''}`}
              onClick={() => setOrientation('portrait')}
            >
              <div className="orientation-icon">
                <Smartphone className="w-8 h-8 rotate-90" />
              </div>
              <h6 className="mb-1 font-semibold">Portrait</h6>
              <small className="text-gray-500">9:16 (1080x1920)</small>
            </div>
            <div 
              className={`orientation-option ${orientation === 'landscape' ? 'selected' : ''}`}
              onClick={() => setOrientation('landscape')}
            >
              <div className="orientation-icon">
                <Monitor className="w-8 h-8" />
              </div>
              <h6 className="mb-1 font-semibold">Landscape</h6>
              <small className="text-gray-500">16:9 (1920x1080)</small>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <label className="block mb-2 font-bold text-gray-700">Subtitle Animation</label>
          <select 
            className="form-control-custom appearance-none bg-no-repeat bg-[right_1rem_center] bg-[length:1em_1em]"
            style={{ backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23343a40' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m2 5 6 6 6-6'/%3e%3c/svg%3e")` }}
            value={subtitleStyle}
            onChange={(e) => setSubtitleStyle(e.target.value)}
          >
            <option value="static">Static (Default)</option>
            <option value="scroll_up">Scroll Up (Movie Credits)</option>
          </select>
          <small className="text-gray-500 mt-1 block">Choose how your subtitles appear on screen</small>
        </div>
        
        <div className="flex justify-between mt-8">
          <button className="px-6 py-2 border-2 border-gray-200 rounded-lg text-gray-400 font-semibold cursor-not-allowed" disabled>
            Previous
          </button>
          <button className="btn-primary-custom" onClick={nextStep}>
            Next: Write Script
          </button>
        </div>
      </div>
    </div>
  );
};

const getLanguageName = (code) => {
  const langNames = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
    'it': 'Italian', 'pt': 'Portuguese', 'hi': 'Hindi', 'ar': 'Arabic',
    'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean', 'ta': 'Tamil'
  };
  return langNames[code] || code.toUpperCase();
};

export default VideoDetailsStep;
