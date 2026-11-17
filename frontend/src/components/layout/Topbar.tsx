import React from 'react';
import { Menu } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { NAV_ITEMS } from './Sidebar';

export const Topbar: React.FC = () => {
  const { activeSection, setIsMobileDrawerOpen } = useApp();
  const label = NAV_ITEMS.find((n) => n.id === activeSection)?.label;
  return (
    <header className="h-14 bg-white border-b border-[#d9ddd7] flex items-center gap-3 px-4 md:hidden sticky top-0 z-30">
      <button
        aria-label="Open navigation"
        className="p-2 -ml-2 rounded hover:bg-[#eef0ec] transition-colors duration-200"
        onClick={() => setIsMobileDrawerOpen(true)}
      >
        <Menu className="w-5 h-5" />
      </button>
      <span className="font-semibold text-sm truncate">{label}</span>
    </header>
  );
};
