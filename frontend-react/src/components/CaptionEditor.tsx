import React from 'react';
import { Type } from 'lucide-react';

interface CaptionEditorProps {
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
}

const CaptionEditor: React.FC<CaptionEditorProps> = ({ 
  value, onChange, maxLength = 2200 
}) => {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <label className="block text-sm font-medium text-gray-700 flex items-center">
          <Type className="w-4 h-4 mr-2" />
          Caption
        </label>
        <span className={`text-xs ${value.length > maxLength ? 'text-red-500 font-bold' : 'text-gray-500'}`}>
          {value.length} / {maxLength}
        </span>
      </div>
      
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
        placeholder="Write a caption for your video..."
      />
      
      <div className="flex flex-wrap gap-2">
        {['#viral', '#shorts', '#trending', '#fyp'].map(tag => (
          <button
            key={tag}
            onClick={() => onChange(value ? `${value} ${tag}` : tag)}
            className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-1 rounded-full transition-colors"
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  );
};

export default CaptionEditor;
