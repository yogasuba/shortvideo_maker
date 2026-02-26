import React from 'react';
import { Film, RotateCcw, Moon, Sun, Calendar, Share2, Clock } from 'lucide-react';
import { ViewType } from '../types';

interface HeaderProps {
  resetForm: () => void;
  toggleTheme: () => void;
  isDarkTheme: boolean;
  setView: (view: ViewType) => void;
  isCalendarView: boolean;
  isIntegrationsView: boolean;
  isHistoryView: boolean;
  isCreatorView: boolean;
  showHistory: () => void;
}

const Header: React.FC<HeaderProps> = ({ resetForm, toggleTheme, isDarkTheme, setView, isCalendarView, isIntegrationsView, isHistoryView, isCreatorView, showHistory }) => {
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
              className={`btn ${isCreatorView ? 'btn-primary-custom' : 'btn-outline-primary'} flex items-center`} 
              onClick={() => {
                resetForm();
                setView('creator');
              }}
            >
              <RotateCcw className="w-4 h-4 mr-1" /> New
            </button>
             <button className={`btn ${isHistoryView ? 'btn-primary-custom' : 'btn-outline-primary'} mr-2 flex items-center`} onClick={showHistory}>
              <Clock className="w-4 h-4 mr-1" /> History
            </button>
            <button 
              className={`btn ${isCalendarView ? 'btn-primary-custom' : 'btn-outline-primary'} flex items-center`} 
              onClick={() => setView('calendar')}
            >
              <Calendar className="w-4 h-4 mr-1" /> Calendar
            </button>
            <button 
              className={`btn ${isIntegrationsView ? 'btn-primary-custom' : 'btn-outline-primary'} flex items-center ml-2`} 
              onClick={() => setView('integrations')}
            >
              <Share2 className="w-4 h-4 mr-1" /> Integrations
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
