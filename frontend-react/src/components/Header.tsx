import React from 'react';
import { Film, RotateCcw, Moon, Sun, Calendar } from 'lucide-react';
import { ViewType } from '../types';

interface HeaderProps {
  resetForm: () => void;
  toggleTheme: () => void;
  isDarkTheme: boolean;
  setView: (view: ViewType) => void;
  isCalendarView: boolean;
}

const Header: React.FC<HeaderProps> = ({ resetForm, toggleTheme, isDarkTheme, setView, isCalendarView }) => {
  return (
    <div className="header">
      <div className="container-custom">
        <div className="flex justify-between items-center">
          <div className="logo cursor-pointer" onClick={() => setView('creator')}>
            <Film className="mr-2" />
            Faceless Videos
          </div>
          <div className="flex items-center gap-2">
            <button 
              className={`btn ${!isCalendarView ? 'btn-primary-custom' : 'btn-outline-primary'} flex items-center`} 
              onClick={() => {
                resetForm();
                setView('creator');
              }}
            >
              <RotateCcw className="w-4 h-4 mr-1" /> New
            </button>
            <button 
              className={`btn ${isCalendarView ? 'btn-primary-custom' : 'btn-outline-primary'} flex items-center`} 
              onClick={() => setView('calendar')}
            >
              <Calendar className="w-4 h-4 mr-1" /> Calendar
            </button>
            <button className="btn-primary-custom inline-flex items-center justify-center min-w-[45px] ml-2" onClick={toggleTheme}>
              {isDarkTheme ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header;
