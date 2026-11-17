import React, { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
    label?: string;
  };
  highlight?: boolean;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  highlight = false,
  className,
}) => {
  return (
    <div
      className={cn(
        'bg-white border rounded-lg p-4 transition-all duration-200 relative overflow-hidden',
        highlight ? 'border-[#246B4B] shadow-sm ring-1 ring-[#246B4B]/10' : 'border-[#E5E8E3] hover:border-[#D1D5DB]',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-semibold tracking-wider text-[#777F79] uppercase">{title}</p>
          <div className="flex items-baseline space-x-2 mt-1">
            <h3 className="text-2xl font-bold text-[#202522] tracking-tight">{value}</h3>
            {trend && (
              <span
                className={cn(
                  'text-xs font-semibold px-1.5 py-0.5 rounded',
                  trend.isPositive ? 'text-[#27845B] bg-[#EBF7F1]' : 'text-[#C44747] bg-rose-50'
                )}
              >
                {trend.value}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-[#777F79] mt-1">{subtitle}</p>}
        </div>
        {icon && (
          <div className="p-2.5 rounded-md bg-[#F7F6F2] text-[#246B4B] border border-[#E5E8E3]">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-[#F0F2EE] flex items-center justify-between text-[10px] text-[#777F79]">
        <span>Demonstration metric</span>
        <span className="font-mono text-[9px] bg-[#F7F6F2] px-1 py-0.5 rounded text-[#202522]">SIMULATED</span>
      </div>
    </div>
  );
};

