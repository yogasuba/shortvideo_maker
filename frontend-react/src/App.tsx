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
import CalendarView from './components/CalendarView';
import IntegrationsView from './components/IntegrationsView';
import Toast from './components/Toast';
import PostizCallback from './components/PostizCallback';
import type { 
  ApiResponse, 
  ConfigData, 
  ProjectStatus, 
  ScenesPreview,
  Alert,
  AlertType,
  ViewType,
  OrientationType,
  SubtitleStyleType,
  ToneType,
  UsePersistentStateReturn
} from './types';

const API_BASE = 'http://localhost:8001';

// Helper to persist state
const usePersistentState = <T,>(key: string, defaultValue: T): UsePersistentStateReturn<T> => {
  const [state, setState] = useState<T>(() => {
    const saved = localStorage.getItem(key);
    if (saved !== null) {
      try {
        return JSON.parse(saved) as T;
      } catch {
        return saved as T;
      }
    }
    return defaultValue;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(state));
  }, [key, state]);

  return [state, setState];
};

function App(): React.JSX.Element {
  // Global State
  const [currentStep, setCurrentStep] = usePersistentState<number>('currentStep', 1);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  
  // Step 1: Video Details
  const [videoTitle, setVideoTitle] = usePersistentState<string>('videoTitle', '');
  const [language, setLanguage] = usePersistentState<string>('language', 'en');
  const [tone, setTone] = usePersistentState<ToneType>('tone', 'neutral');
  const [scenesCount, setScenesCount] = usePersistentState<number>('scenesCount', 8);
  const [orientation, setOrientation] = usePersistentState<OrientationType>('orientation', 'portrait');
  const [resolution, setResolution] = usePersistentState<string>('resolution', '1080x1920');
  const [subtitleStyle, setSubtitleStyle] = usePersistentState<SubtitleStyleType>('subtitleStyle', 'static');
  
  // Step 2: Script
  const [script, setScript] = usePersistentState<string>('script', '');
  const [scenesPreview, setScenesPreview] = useState<ScenesPreview | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  
  // Step 3: Voice
  const [selectedVoice, setSelectedVoice] = usePersistentState<string>('selectedVoice', '');
  
  // Step 4: Style
  const [selectedStyle, setSelectedStyle] = usePersistentState<string>('selectedStyle', 'pexels');
  
  // Step 5: Generation / Progress
  const [currentProjectId, setCurrentProjectId] = usePersistentState<string>('currentProjectId', '');
  const [currentVideoUrl, setCurrentVideoUrl] = usePersistentState<string>('currentVideoUrl', '');
  const [progress, setProgress] = useState<number>(0);
  const [progressStatus, setProgressStatus] = useState<string>('Preparing your video...');
  const [progressDetail, setProgressDetail] = useState<string>("We're splitting your script into scenes and generating assets.");
  const [isCompleted, setIsCompleted] = usePersistentState<boolean>('isCompleted', false);
  const [isGenerating, setIsGenerating] = usePersistentState<boolean>('isGenerating', false);
  
  // Theme
  const [isDarkTheme, setIsDarkTheme] = useState<boolean>(false);
  const [view, setView] = useState<ViewType>('creator'); // 'creator' or 'calendar'

  // Toast State
  const [toast, setToast] = useState<{message: string, type: 'success' | 'error' | 'info' | 'warning'} | null>(null);

  // Load configuration
  useEffect(() => {
    const loadConfiguration = async (): Promise<void> => {
      try {
        const response = await fetch(`${API_BASE}/api/config`);
        const data: ApiResponse<ConfigData> = await response.json();
        if (data.success && data.data) {
          setConfig(data.data);
        }
      } catch (error) {
        addAlert('Failed to load configuration. Make sure the backend server is running on port 8001.', 'error');
      }
    };
    loadConfiguration();
  }, []);

  const addAlert = (message: string, type: AlertType = 'info'): void => {
    setToast({ message, type });
  };

  const removeAlert = (id: number): void => {
    setAlerts(prev => prev.filter(a => a.id !== id));
  };

  const nextStep = (step: number): void => {
    if (!validateStep(currentStep)) return;
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const prevStep = (step: number): void => {
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const validateStep = (step: number): boolean => {
    if (step === 1) {
      if (!videoTitle?.trim()) {
        addAlert('Please enter a video title', 'error');
        return false;
      }
      return true;
    } else if (step === 2) {
      if (!script?.trim()) {
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

  const createVideo = async (): Promise<void> => {
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
    setIsCompleted(false);
    setProgress(0);
    
    try {
      const response = await fetch(`${API_BASE}/api/videos/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });
      const data: ApiResponse<{ project_id: string }> = await response.json();
      if (data.success && data.data) {
        setCurrentProjectId(data.data.project_id);
      } else {
        throw new Error('Failed to start video creation');
      }
    } catch (error) {
      addAlert(`Error: ${(error as Error).message}`, 'error');
      setCurrentStep(4);
      setIsGenerating(false);
    }
  };

  // Poll for progress if generating
  useEffect(() => {
    if (!isGenerating || !currentProjectId) return;

    let intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/api/projects/${currentProjectId}/status`);
        const data: ApiResponse<ProjectStatus> = await response.json();
        
        if (data.success && data.data) {
          const project = data.data;
          updateProgressState(project);
          
          if (project.status === 'completed') {
            setCurrentVideoUrl(project.video_url || '');
            setIsCompleted(true);
            setIsGenerating(false);
            clearInterval(intervalId);
          } else if (project.status === 'failed') {
            const errorMessage = typeof project.error === 'string' 
              ? project.error 
              : project.error?.message || 'Unknown error';
            addAlert(`Video creation failed: ${errorMessage}`, 'error');
            setIsGenerating(false);
            clearInterval(intervalId);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [isGenerating, currentProjectId]);

  const updateProgressState = (project: ProjectStatus): void => {
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

  const resetForm = (): void => {
    localStorage.clear();
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

  const toggleTheme = (): void => {
    setIsDarkTheme(!isDarkTheme);
    document.body.classList.toggle('dark-theme');
  };


  // Handle routing for OAuth callbacks (Headless Postiz)
  const [isCallback, setIsCallback] = useState(false);
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('postiz_callback') === 'true' || window.location.pathname.startsWith('/integrations/social/')) {
      setIsCallback(true);
    }
  }, []);

  if (isCallback) {
    return <PostizCallback />;
  }

  return (
    <div className={isDarkTheme ? 'dark-theme' : ''}>
      <Header 
        resetForm={resetForm} 
        toggleTheme={toggleTheme} 
        isDarkTheme={isDarkTheme} 
        setView={setView}
        isCalendarView={view === 'calendar'}
        isIntegrationsView={view === 'integrations'}
      />
      
      <div className="container-custom">
        {view === 'calendar' ? (
          <CalendarView API_BASE={API_BASE} setView={setView} />
        ) : view === 'integrations' ? (
          <IntegrationsView API_BASE={API_BASE} addAlert={addAlert} />
        ) : (
          <>
            <StepIndicator currentStep={currentStep} />
            
            {/* Replaced AlertContainer with Toast */}
            {toast && (
              <Toast 
                message={toast.message}
                type={toast.type}
                onClose={() => setToast(null)}
              />
            )}
            
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
            setOrientation={(o: OrientationType) => {
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
            projectId={currentProjectId}
            orientation={orientation}
            resetForm={resetForm}
            API_BASE={API_BASE}
            addAlert={addAlert}
          />
        )}
          </>
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
