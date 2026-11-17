import React from 'react';
import { useApp } from '@/context/AppContext';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-sm w-full pointer-events-none">
      {toasts.map(toast => {
        let icon = <CheckCircle2 className="w-4 h-4 text-[#27845B]" />;
        let borderColor = 'border-[#27845B]/30';
        let bg = 'bg-white';

        if (toast.type === 'error') {
          icon = <AlertCircle className="w-4 h-4 text-[#C44747]" />;
          borderColor = 'border-[#C44747]/30';
        } else if (toast.type === 'warning') {
          icon = <AlertTriangle className="w-4 h-4 text-[#D97736]" />;
          borderColor = 'border-[#D97736]/30';
        } else if (toast.type === 'info') {
          icon = <Info className="w-4 h-4 text-[#246B4B]" />;
          borderColor = 'border-[#246B4B]/30';
        }

        return (
          <div
            key={toast.id}
            className={cn(
              'pointer-events-auto p-3.5 rounded-lg border shadow-md flex items-start space-x-3 transition-all duration-200',
              bg,
              borderColor
            )}
          >
            <div className="shrink-0 mt-0.5">{icon}</div>
            <div className="flex-1 min-w-0">
              {toast.title && <h5 className="text-xs font-semibold text-[#202522]">{toast.title}</h5>}
              <p className="text-xs text-[#777F79] leading-relaxed">{toast.message}</p>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

