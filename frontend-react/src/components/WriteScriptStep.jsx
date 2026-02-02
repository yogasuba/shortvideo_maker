import React from 'react';
import { Pencil, Eye } from 'lucide-react';

const WriteScriptStep = ({ 
  script, setScript, 
  language, scenesCount, 
  setScenesPreview, setShowPreviewModal,
  prevStep, nextStep, addAlert, API_BASE 
}) => {
  
  const scriptCount = script.length;
  
  const examples = {
    ai: `Artificial intelligence is revolutionizing every industry. From healthcare diagnostics to autonomous vehicles, AI is making our lives easier and more efficient...`,
    meditation: `Meditation offers numerous benefits for both mental and physical health. Just 10 minutes of daily practice can transform your life...`,
    entrepreneur: `Starting a business begins with a great idea. But an idea alone isn't enough – execution is everything...`
  };

  // Note: Full examples taken from index.html (I'll truncate here for brevity but ideally use full text)
  const loadExample = (type) => {
    // In actual implementation, I should use the full text from index.html
    const fullExamples = {
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
    
    // Simulate loading state (original logic had this inside the function)
    const originalBtnContent = document.getElementById('previewBtn')?.innerHTML;
    if (document.getElementById('previewBtn')) {
      document.getElementById('previewBtn').disabled = true;
      document.getElementById('previewBtn').innerHTML = '<span class="loading-spinner"></span> Analyzing script...';
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
      const data = await response.json();
      if (data.success) {
        setScenesPreview(data.data);
        setShowPreviewModal(true);
      } else {
        throw new Error('Failed to preview script');
      }
    } catch (error) {
      addAlert(`Error: ${error.message}`, 'error');
    } finally {
      if (document.getElementById('previewBtn')) {
        document.getElementById('previewBtn').disabled = false;
        document.getElementById('previewBtn').innerHTML = '<i class="lucide-eye mr-2"></i> Preview Split Scene';
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
            onChange={(e) => setScript(e.target.value)}
            placeholder="Write or paste your entire script here..."
            maxLength={5000}
          />
          <div className={`character-count ${scriptCount > 4500 ? (scriptCount > 5000 ? 'error' : 'warning') : ''}`}>
            {scriptCount}/5000
          </div>
        </div>
        
        <button 
          className="btn-primary-custom w-full py-4 flex items-center justify-center" 
          onClick={previewScriptSplit}
          id="previewBtn"
        >
          <Eye className="mr-2" /> Preview Split Scene
        </button>
        
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
