import React from 'react';
import { Palette, Image, Film } from 'lucide-react';

const ImageStyleStep = ({ 
  config, selectedStyle, setSelectedStyle, prevStep, createVideo 
}) => {
  
  const getStyleIcon = (styleId) => {
    const icons = {
      'pexels': <Image className="w-8 h-8" />
    };
    return icons[styleId] || <Image className="w-8 h-8" />;
  };

  return (
    <div className="card-custom">
      <div className="card-header-custom flex items-center">
        <Palette className="mr-2" />
        <h4 className="mb-0 text-xl font-semibold">Choose an Image Style</h4>
      </div>
      <div className="card-body p-6">
        <p className="text-gray-500 mb-6">Select the style for your content's images</p>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {config?.image_styles?.map((style) => (
            <div 
              key={style.id}
              className={`style-option ${selectedStyle === style.id ? 'selected' : ''}`}
              onClick={() => setSelectedStyle(style.id)}
            >
              <div className="style-icon">
                {getStyleIcon(style.id)}
              </div>
              <h6 className="mb-1 font-semibold">{style.name}</h6>
              <small className="text-gray-500 line-clamp-2">{style.description}</small>
            </div>
          ))}
        </div>
        
        <div className="flex justify-between mt-8">
          <button className="px-6 py-2 border-2 border-gray-200 rounded-lg text-gray-700 font-semibold hover:bg-gray-50" onClick={prevStep}>
            Previous
          </button>
          <button className="btn-primary-custom flex items-center" onClick={createVideo} id="createVideoBtn">
            <Film className="mr-2 w-5 h-5" /> Create Video
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImageStyleStep;
