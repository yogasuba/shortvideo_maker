import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import StepIndicator from './components/StepIndicator';
import ImageStyleStep from './components/ImageStyleStep';
import AlertContainer from './components/AlertContainer';
import VideoDetailsStep from './components/VideoDetailsStep';
import WriteScriptStep from './components/WriteScriptStep';
import ChooseVoiceStep from './components/ChooseVoiceStep';
import GenerationProgressStep from './components/GenerationProgressStep';
import ScenePreviewModal from './components/ScenePreviewModal';

const API_BASE = 'http://localhost:8001';

function App() {
  // Global State
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState(null);
  const [alerts, setAlerts] = useState([]);
  
  // Step 1: Video Details
  const [videoTitle, setVideoTitle] = useState('');
  const [language, setLanguage] = useState('en');
  const [tone, setTone] = useState('neutral');
  const [scenesCount, setScenesCount] = useState(8);
  const [orientation, setOrientation] = useState('portrait');
  const [resolution, setResolution] = useState('1080x1920');
  const [subtitleStyle, setSubtitleStyle] = useState('static');
  
  // Step 2: Script
  const [script, setScript] = useState('');
  const [scenesPreview, setScenesPreview] = useState(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  
  // Step 3: Voice
  const [selectedVoice, setSelectedVoice] = useState('');
  
  // Step 4: Style
  const [selectedStyle, setSelectedStyle] = useState('pexels');
  
  // Step 5: Generation / Progress
  const [currentProjectId, setCurrentProjectId] = useState('');
  const [currentVideoUrl, setCurrentVideoUrl] = useState('');
  const [progress, setProgress] = useState(0);
  const [progressStatus, setProgressStatus] = useState('Preparing your video...');
  const [progressDetail, setProgressDetail] = useState("We're splitting your script into scenes and generating assets.");
  const [isCompleted, setIsCompleted] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Theme
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  // Load configuration
  useEffect(() => {
    const loadConfiguration = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/config`);
        const data = await response.json();
        if (data.success) {
          setConfig(data.data);
        }
      } catch (error) {
        addAlert('Failed to load configuration. Make sure the backend server is running on port 8001.', 'error');
      }
    };
    loadConfiguration();
  }, []);

  const addAlert = (message, type = 'info') => {
    const id = Date.now();
    setAlerts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      removeAlert(id);
    }, 5000);
  };

  const removeAlert = (id) => {
    setAlerts(prev => prev.filter(a => a.id !== id));
  };

  const nextStep = (step) => {
    if (!validateStep(currentStep)) return;
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const prevStep = (step) => {
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const validateStep = (step) => {
    if (step === 1) {
      if (!videoTitle.trim()) {
        addAlert('Please enter a video title', 'error');
        return false;
      }
      return true;
    } else if (step === 2) {
      if (!script.trim()) {
        addAlert('Please enter your script', 'error');
        return false;
      }
      if (script.length < 50) {
        addAlert('Script should be at least 50 characters long', 'error');
        return false;
      }
      return true;
    } else if (step === 3) {
      if (!selectedVoice) {
        addAlert('Please select a voice', 'error');
        return false;
      }
      return true;
    } else if (step === 4) {
      if (!selectedStyle) {
        addAlert('Please select an image style', 'error');
        return false;
      }
      return true;
    }
    return true;
  };

  const createVideo = async () => {
    if (!validateStep(4)) return;
    
    const requestData = {
      title: videoTitle.trim(),
      script: script.trim(),
      language,
      tone,
      voice: selectedVoice,
      image_style: selectedStyle,
      resolution,
      scenes_count: scenesCount,
      subtitle_style: subtitleStyle,
      scenes: scenesPreview ? scenesPreview.scenes : null
    };
    
    setCurrentStep(5);
    setIsGenerating(true);
    
    try {
      const response = await fetch(`${API_BASE}/api/videos/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });
      const data = await response.json();
      if (data.success) {
        setCurrentProjectId(data.data.project_id);
        startProgressPolling(data.data.project_id);
      } else {
        throw new Error('Failed to start video creation');
      }
    } catch (error) {
      addAlert(`Error: ${error.message}`, 'error');
      setCurrentStep(4);
      setIsGenerating(false);
    }
  };

  const startProgressPolling = (projectId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/api/projects/${projectId}/status`);
        const data = await response.json();
        
        if (data.success) {
          const project = data.data;
          updateProgressState(project);
          
          if (project.status === 'completed') {
            clearInterval(interval);
            setCurrentVideoUrl(project.video_url);
            setIsCompleted(true);
            setIsGenerating(false);
          } else if (project.status === 'failed') {
            clearInterval(interval);
            addAlert(`Video creation failed: ${project.error}`, 'error');
            setCurrentStep(4);
            setIsGenerating(false);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000);
  };

  const updateProgressState = (project) => {
    const p = project.progress || 0;
    setProgress(p);
    
    if (p < 25) {
      setProgressStatus('Processing your script...');
      setProgressDetail('Splitting into scenes and analyzing content');
    } else if (p < 50) {
      setProgressStatus('Generating audio narration...');
      setProgressDetail('Creating voiceovers for each scene');
    } else if (p < 75) {
      setProgressStatus('Creating visuals...');
      setProgressDetail('Generating images for each scene in selected style');
    } else {
      setProgressStatus('Stitching video together...');
      setProgressDetail('Combining all scenes into final video');
    }
  };

  const resetForm = () => {
    setVideoTitle('');
    setScript('');
    setLanguage('en');
    setTone('neutral');
    setScenesCount(8);
    setSelectedVoice('');
    setSelectedStyle('');
    setOrientation('portrait');
    setResolution('1080x1920');
    setCurrentProjectId('');
    setCurrentVideoUrl('');
    setScenesPreview(null);
    setProgress(0);
    setIsCompleted(false);
    setIsGenerating(false);
    setCurrentStep(1);
    addAlert('Ready to create another video!', 'success');
  };

  const toggleTheme = () => {
    setIsDarkTheme(!isDarkTheme);
    document.body.classList.toggle('dark-theme');
  };

  return (
    <div className={isDarkTheme ? 'dark-theme' : ''}>
      <Header 
        resetForm={resetForm} 
        toggleTheme={toggleTheme} 
        isDarkTheme={isDarkTheme} 
      />
      
      <div className="container-custom">
        <StepIndicator currentStep={currentStep} />
        <AlertContainer alerts={alerts} removeAlert={removeAlert} />
        
        {currentStep === 1 && (
          <VideoDetailsStep 
            videoTitle={videoTitle}
            setVideoTitle={setVideoTitle}
            language={language}
            setLanguage={setLanguage}
            tone={tone}
            setTone={setTone}
            scenesCount={scenesCount}
            setScenesCount={setScenesCount}
            orientation={orientation}
            setOrientation={(o) => {
              setOrientation(o);
              setResolution(o === 'portrait' ? '1080x1920' : '1920x1080');
            }}
            subtitleStyle={subtitleStyle}
            setSubtitleStyle={setSubtitleStyle}
            nextStep={() => nextStep(2)}
            config={config}
          />
        )}
        
        {currentStep === 2 && (
          <WriteScriptStep 
            script={script}
            setScript={setScript}
            language={language}
            scenesCount={scenesCount}
            scenesPreview={scenesPreview}
            setScenesPreview={setScenesPreview}
            setShowPreviewModal={setShowPreviewModal}
            prevStep={() => prevStep(1)}
            nextStep={() => nextStep(3)}
            addAlert={addAlert}
            API_BASE={API_BASE}
          />
        )}
        
        {currentStep === 3 && (
          <ChooseVoiceStep 
            config={config}
            selectedVoice={selectedVoice}
            setSelectedVoice={setSelectedVoice}
            language={language}
            prevStep={() => prevStep(2)}
            nextStep={() => nextStep(4)}
            API_BASE={API_BASE}
          />
        )}
        
        {currentStep === 4 && (
          <ImageStyleStep 
            config={config}
            selectedStyle={selectedStyle}
            setSelectedStyle={setSelectedStyle}
            prevStep={() => prevStep(3)}
            createVideo={createVideo}
          />
        )}
        
        {currentStep === 5 && (
          <GenerationProgressStep 
            progress={progress}
            progressStatus={progressStatus}
            progressDetail={progressDetail}
            isCompleted={isCompleted}
            videoTitle={videoTitle}
            videoUrl={currentVideoUrl}
            orientation={orientation}
            resetForm={resetForm}
            API_BASE={API_BASE}
            addAlert={addAlert}
          />
        )}
      </div>

      {showPreviewModal && scenesPreview && (
        <ScenePreviewModal 
          data={scenesPreview}
          setScenesPreview={setScenesPreview}
          onClose={() => setShowPreviewModal(false)}
          onProceed={() => {
            setShowPreviewModal(false);
            setCurrentStep(3);
          }}
          API_BASE={API_BASE}
          addAlert={addAlert}
        />
      )}
    </div>
  );
}


export default App;
