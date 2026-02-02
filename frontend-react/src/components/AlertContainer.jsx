import React from 'react';
import { X } from 'lucide-react';

const AlertContainer = ({ alerts, removeAlert }) => {
  return (
    <div className="mb-4 space-y-2">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`alert-custom relative flex justify-between items-center bg-${alert.type === 'error' ? 'red-100 text-red-800' : alert.type === 'success' ? 'green-100 text-green-800' : 'blue-100 text-blue-800'}`}
        >
          <span>{alert.message}</span>
          <button
            type="button"
            className="p-1 hover:bg-black/5 rounded transition-colors"
            onClick={() => removeAlert(alert.id)}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
};

export default AlertContainer;
