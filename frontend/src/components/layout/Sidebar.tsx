import React from 'react';
import { useApp } from '@/context/AppContext';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { NAV_ITEMS } from './navItems';

export const Sidebar: React.FC = () => {
  const { activeSection, setActiveSection, isMobileDrawerOpen, setIsMobileDrawerOpen } = useApp();

  const nav = (
    <nav aria-label="Main" className="flex flex-col h-full bg-[#202522] text-[#F7F6F2]">
      <div className="h-16 flex items-center justify-between px-4 border-b border-[#3a423d]">
        <div className="leading-tight">
          <div className="font-bold text-sm text-white">SupeRR Selector</div>
          <div className="text-xs text-[#e9a273]">Season 2 | Pressure analysis</div>
        </div>
        <button
          className="md:hidden p-1.5 rounded text-[#d6dad7] hover:bg-[#2f3631] transition-colors duration-200"
          aria-label="Close navigation"
          onClick={() => setIsMobileDrawerOpen(false)}
        >
          <X className="w-5 h-5" />
        </button>
      </div>
      <ul className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = activeSection === item.id;
          return (
            <li key={item.id}>
              <button
                onClick={() => {
                  setActiveSection(item.id);
                  setIsMobileDrawerOpen(false);
                }}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'w-full flex items-center gap-2.5 rounded px-3 py-2 text-left text-sm transition-colors duration-200',
                  active ? 'bg-[#246B4B] text-white font-semibold' : 'text-[#d6dad7] hover:bg-[#2f3631] hover:text-white',
                )}
              >
                <span aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="p-3 border-t border-[#3a423d] text-xs text-[#c3c9c5]">
        Descriptive profiles carry no rank or score.
      </div>
    </nav>
  );

  return (
    <>
      <aside className="hidden md:block w-64 shrink-0 h-screen sticky top-0">{nav}</aside>
      {isMobileDrawerOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 md:hidden" onClick={() => setIsMobileDrawerOpen(false)} aria-hidden="true" />
      )}
      <div
        className={cn(
          'fixed inset-y-0 left-0 w-72 max-w-[85vw] z-50 md:hidden transition-transform duration-200',
          isMobileDrawerOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        aria-hidden={!isMobileDrawerOpen}
        {...(!isMobileDrawerOpen ? { inert: true } : {})}
      >
        {nav}
      </div>
    </>
  );
};
