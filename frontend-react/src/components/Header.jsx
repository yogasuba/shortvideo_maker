import React from 'react';
import { Film, RotateCcw, Moon, Sun } from 'lucide-react';

const Header = ({ resetForm, toggleTheme, isDarkTheme }) => {
  return (
    <div className="header">
      <div className="container-custom">
        <div className="flex justify-between items-center">
          <div className="logo">
            <Film className="mr-2" />
            Faceless Videos
          </div>
          <div>
            <button className="btn btn-outline-primary mr-2 flex items-center" onClick={resetForm}>
              <RotateCcw className="w-4 h-4 mr-1" /> New
            </button>
            <button className="btn-primary-custom flex items-center justify-center min-w-[45px]" onClick={toggleTheme}>
              {isDarkTheme ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header;
