import React,{useState} from 'react';
import { Pencil, Eye, Settings2 } from 'lucide-react';
import { ScenesPreview, ApiResponse, AlertType } from '../types';

interface WriteScriptStepProps {
  script: string;
  setScript: (script: string) => void;
  language: string;
  scenesCount: number;
  scenesPreview: ScenesPreview | null;
  setScenesPreview: (preview: ScenesPreview) => void;
  setShowPreviewModal: (show: boolean) => void;
  prevStep: () => void;
  nextStep: () => void;
  addAlert: (message: string, type: AlertType) => void;
  API_BASE: string;
}

const WriteScriptStep: React.FC<WriteScriptStepProps> = ({ 
  script, setScript, 
  language, scenesCount, 
  scenesPreview, setScenesPreview, setShowPreviewModal,
  prevStep, nextStep, addAlert, API_BASE 
}) => {
  const [lastScript, setLastScript] = useState(scenesPreview ? script : '');
  
  const scriptCount = script.length;
  
  type ExampleType = 'ai' | 'meditation' | 'entrepreneur';

  const examples: Record<ExampleType, string> = {
    ai: `Artificial intelligence is revolutionizing every industry. From healthcare diagnostics to autonomous vehicles, AI is making our lives easier and more efficient...`,
    meditation: `Meditation offers numerous benefits for both mental and physical health. Just 10 minutes of daily practice can transform your life...`,
    entrepreneur: `Starting a business begins with a great idea. But an idea alone isn't enough – execution is everything...`
  };

  const loadExample = (type: ExampleType) => {
    const fullExamples: Record<ExampleType, string> = {
      ai: `Artificial intelligence is revolutionizing every industry. From healthcare diagnostics to autonomous vehicles, AI is making our lives easier and more efficient.\n\nThe key benefits include increased productivity, improved accuracy, and significant cost reduction. Machine learning algorithms can process vast amounts of data in seconds.\n\nAs technology advances, we can expect even more innovative applications. AI will help solve complex problems like climate change and disease prevention.\n\nThe future is bright for AI development. With responsible implementation, we can create a better world for everyone.`,
      meditation: `Meditation offers numerous benefits for both mental and physical health. Just 10 minutes of daily practice can transform your life.\n\nRegular meditation reduces stress and anxiety levels significantly. It helps calm the mind and improve emotional regulation.\n\nStudies show meditation increases focus and concentration. It enhances creativity and problem-solving abilities.\n\nPhysical benefits include lower blood pressure and improved sleep quality. Meditation strengthens the immune system and promotes longevity.\n\nStarting is simple: find a quiet space, sit comfortably, and focus on your breath. Consistency is more important than duration.`,
      entrepreneur: `Starting a business begins with a great idea. But an idea alone isn't enough – execution is everything.\n\nFirst, validate your concept with market research. Identify your target audience and their pain points.\n\nCreate a simple business plan outlining your goals. Focus on creating minimum viable products to test the market.\n\nBuilding a strong team is crucial for success. Surround yourself with people who complement your skills.\n\nRemember, entrepreneurship is a journey of learning. Embrace failures as opportunities to grow and improve.`
    };
    setScript(fullExamples[type]);
    addAlert(`Loaded "${type}" example script`, 'success');
  };

  const previewScriptSplit = async () => {
    if (!script.trim()) {
      addAlert('Please enter your script first', 'error');
      return;
    }
    
    // Simulate loading state
    const previewBtn = document.getElementById('previewBtn') as HTMLButtonElement | null;
    if (previewBtn) {
      previewBtn.disabled = true;
      previewBtn.innerHTML = '<span class="loading-spinner"></span> Analyzing script...';
    }

    // If script hasn't changed and we already have a preview, just open it
    if (scenesPreview && script === lastScript) {
      setShowPreviewModal(true);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/scripts/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script,
          scenes_count: scenesCount,
          language
        })
      });
      const data: ApiResponse<ScenesPreview> = await response.json();
      if (data.success && data.data) {
        setScenesPreview(data.data);
        setLastScript(script);
        setShowPreviewModal(true);
      } else {
        throw new Error('Failed to preview script');
      }
    } catch (error) {
      addAlert(`Error: ${(error as Error).message}`, 'error');
    } finally {
      if (previewBtn) {
        previewBtn.disabled = false;
        previewBtn.innerHTML = '<i class="lucide-eye mr-2"></i> Preview Split Scene';
      }
    }
  };

  return (
    <div className="card-custom">
      <div className="card-header-custom flex items-center">
        <Pencil className="mr-2" />
        <h4 className="mb-0 text-xl font-semibold">Write Your Script</h4>
      </div>
      <div className="card-body p-6">
        <p className="text-gray-500 mb-6">
          Write or paste your entire script below. We'll automatically split it into scenes and create visuals for each part.
        </p>
        
        <div className="example-scripts">
          <h6 className="font-bold mb-3 text-primary">💡 Try these example scripts:</h6>
          <div className="example-script" onClick={() => loadExample('ai')}>
            <div className="font-semibold text-primary mb-1">🤖 The Future of AI</div>
            <div className="text-[0.9rem] text-gray-500">Artificial intelligence is transforming our world...</div>
          </div>
          <div className="example-script" onClick={() => loadExample('meditation')}>
            <div className="font-semibold text-primary mb-1">🧘 Benefits of Meditation</div>
            <div className="text-[0.9rem] text-gray-500">Meditation reduces stress and improves focus...</div>
          </div>
          <div className="example-script" onClick={() => loadExample('entrepreneur')}>
            <div className="font-semibold text-primary mb-1">🚀 Starting a Business</div>
            <div className="text-[0.9rem] text-gray-500">Becoming an entrepreneur begins with an idea...</div>
          </div>
        </div>
        
        <div className="mb-6">
          <label className="block mb-2 font-bold text-gray-700">Your Script *</label>
          <textarea 
            className="form-control-custom script-input h-[200px]" 
            value={script}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setScript(e.target.value)}
            placeholder="Write or paste your entire script here..."
            maxLength={5000}
          />
          <div className={`character-count ${scriptCount > 4500 ? (scriptCount > 5000 ? 'error' : 'warning') : ''}`}>
            {scriptCount}/5000
          </div>
        </div>
        
        <div className="flex flex-col gap-3">
          <button 
            className="btn-primary-custom w-full py-4 flex items-center justify-center font-bold" 
            onClick={previewScriptSplit}
            id="previewBtn"
          >
            <Eye className="mr-2" /> {scenesPreview && script === lastScript ? 'Re-Analyze Script' : 'Analyze & Preview Split'}
          </button>

          {scenesPreview && (
            <button 
              className="bg-gray-100 text-gray-700 hover:bg-gray-200 w-full py-3 rounded-xl flex items-center justify-center transition-all border border-gray-200"
              onClick={() => setShowPreviewModal(true)}
            >
              <Settings2 className="w-4 h-4 mr-2" /> View/Edit Current Scene Settings
            </button>
          )}
        </div>
        
        <div className="mt-4 text-center">
          <button className="text-gray-500 hover:text-primary transition-colors font-medium" onClick={prevStep}>
            Back to Video Details
          </button>
        </div>
      </div>
    </div>
  );
};

export default WriteScriptStep;
