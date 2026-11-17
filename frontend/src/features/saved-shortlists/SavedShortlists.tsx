import React, { useState, useEffect } from 'react';
import { useApp } from '@/context/AppContext';
import {
  BookmarkCheck,
  Search,
  Download,
  Trash2,
  Edit2,
  Check,
  X,
  FileText,
  Calendar,
  Sparkles,
  User,
  Sliders,
  Scale,
  Coins,
  Shield,
} from 'lucide-react';
import { shortlistService } from '@/services/shortlistService';
import { ShortlistItem } from '@/types';
import { MOCK_PLAYERS } from '@/data/mock/players';

export const SavedShortlists: React.FC = () => {
  const { refreshShortlistCount, openPlayerProfile, addToast } = useApp();

  const [items, setItems] = useState<ShortlistItem[]>([]);
  const [search, setSearch] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('all');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');

  const loadItems = async () => {
    const list = await shortlistService.getShortlists();
    setItems(list);
  };

  useEffect(() => {
    loadItems();
  }, []);

  const handleDelete = async (id: string, title: string) => {
    await shortlistService.remove(id);
    await loadItems();
    await refreshShortlistCount();
    addToast(`Removed "${title}" from shortlists`, 'info');
  };

  const handleStartEdit = (item: ShortlistItem) => {
    setEditingId(item.id);
    setEditTitle(item.title);
    setEditNotes(item.notes);
  };

  const handleSaveEdit = async (id: string) => {
    if (editTitle.trim()) {
      await shortlistService.rename(id, editTitle.trim());
    }
    await shortlistService.updateNotes(id, editNotes.trim());
    setEditingId(null);
    await loadItems();
    addToast('Updated shortlist entry', 'success');
  };

  const handleExportCSV = () => {
    shortlistService.exportShortlistCSV(items);
    addToast('Exported shortlists to CSV', 'success');
  };

  const filteredItems = items
    .filter(item => (filterType === 'all' ? true : item.type === filterType))
    .filter(item =>
      item.title.toLowerCase().includes(search.toLowerCase()) ||
      item.notes.toLowerCase().includes(search.toLowerCase())
    );

  const getItemIcon = (type: ShortlistItem['type']) => {
    switch (type) {
      case 'player':
        return <User className="w-4 h-4 text-[#246B4B]" />;
      case 'custom-ranking':
        return <Sliders className="w-4 h-4 text-[#D97736]" />;
      case 'comparison':
        return <Scale className="w-4 h-4 text-blue-600" />;
      case 'auction-target':
        return <Coins className="w-4 h-4 text-amber-600" />;
      case 'squad':
        return <Shield className="w-4 h-4 text-emerald-600" />;
      default:
        return <FileText className="w-4 h-4 text-[#777F79]" />;
    }
  };

  return (
    <div className="space-y-5">
      {/* Search and Filters Bar */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#777F79] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search saved targets, custom rankings and tactical notes..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-[#F7F6F2] text-xs border border-[#E5E8E3] focus:border-[#246B4B] rounded-lg outline-none transition-colors text-[#202522]"
            />
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={handleExportCSV}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-[#246B4B] hover:bg-[#1b533a] text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export All (CSV)</span>
            </button>
          </div>
        </div>

        {/* Category Pills */}
        <div className="flex items-center space-x-2 pt-2 border-t border-[#E5E8E3] overflow-x-auto text-xs">
          <span className="text-[10px] font-bold text-[#777F79] uppercase">Filter Type:</span>
          {[
            { id: 'all', label: 'All Items' },
            { id: 'player', label: 'Players' },
            { id: 'custom-ranking', label: 'Custom Rankings' },
            { id: 'auction-target', label: 'Auction Targets' },
            { id: 'comparison', label: 'Comparisons' },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setFilterType(f.id)}
              className={`px-3 py-1 rounded-md font-semibold transition-colors cursor-pointer border ${
                filterType === f.id
                  ? 'bg-[#202522] text-white border-[#202522]'
                  : 'bg-[#F7F6F2] hover:bg-stone-200 text-[#202522] border-[#E5E8E3]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Shortlist Items List */}
      {filteredItems.length === 0 ? (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-[#F7F6F2] text-[#777F79] flex items-center justify-center mx-auto">
            <BookmarkCheck className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-bold text-[#202522]">No saved items match your criteria</h4>
          <p className="text-xs text-[#777F79] max-w-sm mx-auto">
            You can bookmark candidates from the Player Explorer, Rankings, or save Custom Top 10 rankings.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredItems.map(item => {
            const isEditing = editingId === item.id;
            const targetPlayer = item.type === 'player' ? MOCK_PLAYERS.find(p => p.id === item.targetId) : null;

            return (
              <div
                key={item.id}
                className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs hover:border-gray-300 transition-all flex flex-col justify-between text-xs space-y-3"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="p-2 rounded-lg bg-[#F7F6F2] border border-[#E5E8E3]">
                        {getItemIcon(item.type)}
                      </div>
                      <div>
                        {isEditing ? (
                          <input
                            type="text"
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                            className="bg-[#F7F6F2] border border-[#246B4B] rounded px-2 py-0.5 text-xs font-bold text-[#202522] outline-none"
                          />
                        ) : (
                          <h4 className="font-bold text-sm text-[#202522]">{item.title}</h4>
                        )}
                        <span className="text-[10px] text-[#777F79] capitalize">
                          Type: {item.type.replace('-', ' ')}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => handleSaveEdit(item.id)}
                            className="p-1 rounded bg-[#246B4B] text-white hover:bg-[#1b533a] cursor-pointer"
                            title="Save changes"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 rounded bg-stone-200 text-[#777F79] hover:bg-stone-300 cursor-pointer"
                            title="Cancel"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => handleStartEdit(item)}
                            className="p-1 rounded hover:bg-stone-100 text-[#777F79] hover:text-[#202522] cursor-pointer"
                            title="Edit notes"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(item.id, item.title)}
                            className="p-1 rounded hover:bg-rose-100 text-[#777F79] hover:text-[#C44747] cursor-pointer"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Notes / Rationale */}
                  <div className="mt-2.5 p-2.5 rounded bg-[#F7F6F2] border border-[#E5E8E3]">
                    <span className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Scouting Notes</span>
                    {isEditing ? (
                      <textarea
                        value={editNotes}
                        onChange={e => setEditNotes(e.target.value)}
                        rows={2}
                        className="w-full bg-white border border-[#246B4B] rounded p-1.5 text-xs text-[#202522] outline-none"
                      />
                    ) : (
                      <p className="text-[#202522] text-xs leading-relaxed">
                        {item.notes || 'No scouting notes attached.'}
                      </p>
                    )}
                  </div>
                </div>

                <div className="pt-2 border-t border-[#E5E8E3] flex items-center justify-between text-[10px] text-[#777F79]">
                  <span className="flex items-center space-x-1">
                    <Calendar className="w-3 h-3 text-[#777F79]" />
                    <span>Saved: {new Date(item.createdAt).toLocaleDateString()}</span>
                  </span>

                  {targetPlayer && (
                    <button
                      onClick={() => openPlayerProfile(targetPlayer)}
                      className="text-[#246B4B] font-bold hover:underline cursor-pointer"
                    >
                      View Profile &rarr;
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

