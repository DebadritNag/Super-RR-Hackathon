import { ShortlistItem } from '@/types';
import { storageAdapter } from '@/lib/storage';
import { exportToCSV } from '@/lib/utils';

export const shortlistService = {
  async getShortlists(): Promise<ShortlistItem[]> {
    return storageAdapter.getShortlists();
  },

  async addPlayer(playerId: string, playerName: string, defaultNote: string = ''): Promise<ShortlistItem> {
    return storageAdapter.addShortlistItem({
      type: 'player',
      title: playerName,
      targetId: playerId,
      notes: defaultNote,
    });
  },

  async addCustomRanking(title: string, playerIds: string[], notes: string = ''): Promise<ShortlistItem> {
    return storageAdapter.addShortlistItem({
      type: 'custom-ranking',
      title,
      targetId: `cr-${Date.now()}`,
      playerIds,
      notes,
    });
  },

  async updateNotes(id: string, notes: string): Promise<ShortlistItem | null> {
    return storageAdapter.updateShortlistItem(id, { notes });
  },

  async rename(id: string, title: string): Promise<ShortlistItem | null> {
    return storageAdapter.updateShortlistItem(id, { title });
  },

  async remove(id: string): Promise<void> {
    storageAdapter.deleteShortlistItem(id);
  },

  exportShortlistCSV(items: ShortlistItem[]): void {
    const headers = ['Type', 'Title', 'Target ID', 'Notes', 'Created At'];
    const rows = items.map(item => [
      item.type,
      item.title,
      item.targetId,
      item.notes,
      item.createdAt,
    ]);
    exportToCSV('superr_selector_shortlist_export', headers, rows);
  },
};

