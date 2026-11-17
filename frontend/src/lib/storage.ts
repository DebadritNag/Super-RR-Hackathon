import { ShortlistItem } from '@/types';
import { INITIAL_SHORTLISTS } from '@/data/mock/shortlists';

const SHORTLIST_STORAGE_KEY = 'superr_selector_shortlists_v1';
const SQUAD_STORAGE_KEY = 'superr_selector_hypothetical_squad_v1';
const SAVED_RANKINGS_KEY = 'superr_selector_saved_rankings_v1';

export const storageAdapter = {
  getShortlists(): ShortlistItem[] {
    try {
      const data = localStorage.getItem(SHORTLIST_STORAGE_KEY);
      if (!data) {
        localStorage.setItem(SHORTLIST_STORAGE_KEY, JSON.stringify(INITIAL_SHORTLISTS));
        return INITIAL_SHORTLISTS;
      }
      return JSON.parse(data);
    } catch {
      return INITIAL_SHORTLISTS;
    }
  },

  saveShortlists(items: ShortlistItem[]): void {
    try {
      localStorage.setItem(SHORTLIST_STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      console.warn('Storage save failed:', e);
    }
  },

  addShortlistItem(item: Omit<ShortlistItem, 'id' | 'createdAt' | 'updatedAt'>): ShortlistItem {
    const current = this.getShortlists();
    const newItem: ShortlistItem = {
      ...item,
      id: `sl-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const updated = [newItem, ...current];
    this.saveShortlists(updated);
    return newItem;
  },

  updateShortlistItem(id: string, updates: Partial<Pick<ShortlistItem, 'title' | 'notes'>>): ShortlistItem | null {
    const current = this.getShortlists();
    let updatedItem: ShortlistItem | null = null;
    const updated = current.map(item => {
      if (item.id === id) {
        updatedItem = { ...item, ...updates, updatedAt: new Date().toISOString() };
        return updatedItem;
      }
      return item;
    });
    this.saveShortlists(updated);
    return updatedItem;
  },

  deleteShortlistItem(id: string): void {
    const current = this.getShortlists();
    const updated = current.filter(item => item.id !== id);
    this.saveShortlists(updated);
  },

  getHypotheticalSquad(): string[] {
    try {
      const data = localStorage.getItem(SQUAD_STORAGE_KEY);
      if (!data) return ['p-101', 'p-109', 'p-110', 'p-201', 'p-202']; // Default RR core
      return JSON.parse(data);
    } catch {
      return ['p-101', 'p-109', 'p-110', 'p-201', 'p-202'];
    }
  },

  saveHypotheticalSquad(playerIds: string[]): void {
    try {
      localStorage.setItem(SQUAD_STORAGE_KEY, JSON.stringify(playerIds));
    } catch (e) {
      console.warn('Storage save failed:', e);
    }
  },

  getSavedRankings(): any[] {
    try {
      const data = localStorage.getItem(SAVED_RANKINGS_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  },

  saveCustomRanking(ranking: any): void {
    try {
      const current = this.getSavedRankings();
      const updated = [ranking, ...current];
      localStorage.setItem(SAVED_RANKINGS_KEY, JSON.stringify(updated));
    } catch (e) {
      console.warn('Storage save failed:', e);
    }
  },
};

