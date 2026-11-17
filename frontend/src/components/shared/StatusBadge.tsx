import React from 'react';
import { DataStatus, InternationalStatus, DataEligibility } from '@/types';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: DataStatus | InternationalStatus | DataEligibility | string;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm', className }) => {
  let badgeStyles = 'bg-gray-100 text-gray-700 border-gray-200';

  switch (status) {
    case 'Verified':
    case 'Verified Capped':
    case 'Eligible':
      badgeStyles = 'bg-[#EBF7F1] text-[#246B4B] border-[#C3E6D6]';
      break;
    case 'Experimental':
    case 'Derived Capped':
      badgeStyles = 'bg-[#FDF3EB] text-[#D97736] border-[#F8DCC9]';
      break;
    case 'Provisional':
    case 'Moderate':
      badgeStyles = 'bg-amber-50 text-amber-800 border-amber-200';
      break;
    case 'Uncapped':
      badgeStyles = 'bg-blue-50 text-blue-700 border-blue-200';
      break;
    case 'Insufficient data':
    case 'Insufficient sample':
    case 'Below data-weight gate':
      badgeStyles = 'bg-rose-50 text-[#C44747] border-rose-200';
      break;
    case 'Restricted':
      badgeStyles = 'bg-red-100 text-red-800 border-red-300';
      break;
    case 'Unknown':
      badgeStyles = 'bg-stone-100 text-stone-600 border-stone-300';
      break;
    default:
      badgeStyles = 'bg-stone-50 text-[#202522] border-[#E5E8E3]';
  }

  const sizeStyles = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded border tracking-tight transition-colors',
        sizeStyles,
        badgeStyles,
        className
      )}
    >
      {status}
    </span>
  );
};

