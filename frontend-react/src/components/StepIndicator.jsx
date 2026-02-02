import React from 'react';

const StepIndicator = ({ currentStep }) => {
  const steps = [
    { id: 1, label: 'Video Details' },
    { id: 2, label: 'Write Script' },
    { id: 3, label: 'Choose Voice' },
    { id: 4, label: 'Image Style' },
    { id: 5, label: 'Generate' },
  ];

  return (
    <div className="step-indicator">
      {steps.map((step) => (
        <div key={step.id} className={`step ${currentStep === step.id ? 'active' : ''}`}>
          <div className="step-circle">{step.id}</div>
          <div className="step-label">{step.label}</div>
        </div>
      ))}
    </div>
  );
};

export default StepIndicator;
