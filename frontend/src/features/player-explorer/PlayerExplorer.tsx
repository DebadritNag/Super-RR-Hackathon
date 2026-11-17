import React, { useState, useEffect, useMemo } from 'react';
import { useApp } from '@/context/AppContext';
import {
  Search,
  Filter,
  Grid,
  List,
  ArrowUpDown,
  Download,
  BookmarkPlus,
  Scale,
  Eye,
  RotateCcw,
  User,
  SlidersHorizontal,
  CheckSquare,
  Square,
  Sparkles,
} from 'lucide-react';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { playerService, PlayerFilterParams } from '@/services/playerService';
import { Player, Nationality, InternationalStatus, PlayerRole, IPLExperience, Speciality, PressureSituation, DataEligibility } from '@/types';
import { exportToCSV, formatScore, formatPercent } from '@/lib/utils';

export const PlayerExplorer: React.FC = () => {
  const {
    openPlayerProfile,
    addToComparison,
    addPlayerToShortlist,
    comparisonPlayerIds,
    addToast,
    globalSearch,
    setGlobalSearch,
  } = useApp();

  // Filters State
  const [search, setSearch] = useState<string>(globalSearch);
  const [nationality, setNationality] = useState<Nationality | 'All'>('All');
  const [internationalStatus, setInternationalStatus] = useState<InternationalStatus | 'All'>('All');
  const [role, setRole] = useState<PlayerRole | 'All'>('All');
  const [iplExperience, setIplExperience] = useState<IPLExperience | 'All'>('All');
  const [speciality, setSpeciality] = useState<Speciality | 'All'>('All');
  const [pressureSituation, setPressureSituation] = useState<PressureSituation | 'All'>('All');
  const [eligibility, setEligibility] = useState<DataEligibility | 'All'>('All');

  // View & Table State
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [sortField, setSortField] = useState<keyof Player>('pressureScore');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>({
    player: true,
    role: true,
    nationality: true,
    status: true,
    experience: true,
    pressureScore: true,
    sampleSize: true,
    reliability: true,
    eligibility: true,
    action: true,
  });

  const [players, setPlayers] = useState<Player[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [matchingCount, setMatchingCount] = useState<number>(0);
  const [eligibleCount, setEligibleCount] = useState<number>(0);

  // Synchronize with global search
  useEffect(() => {
    if (globalSearch !== search) {
      setSearch(globalSearch);
    }
  }, [globalSearch]);

  const loadData = async () => {
    setIsLoading(true);
    const params: PlayerFilterParams = {
      search: search.trim() || undefined,
      nationality,
      internationalStatus,
      role,
      iplExperience,
      speciality,
      pressureSituation,
      eligibility,
      sortBy: sortField,
      sortOrder,
    };

    const res = await playerService.getPlayers(params);
    setPlayers(res.players);
    setTotalCount(res.totalCount);
    setMatchingCount(res.matchingCount);
    setEligibleCount(res.eligibleCount);
    setIsLoading(false);
  };

  useEffect(() => {
    loadData();
    setPage(1);
  }, [search, nationality, internationalStatus, role, iplExperience, speciality, pressureSituation, eligibility, sortField, sortOrder]);

  const handleResetFilters = () => {
    setSearch('');
    setGlobalSearch('');
    setNationality('All');
    setInternationalStatus('All');
    setRole('All');
    setIplExperience('All');
    setSpeciality('All');
    setPressureSituation('All');
    setEligibility('All');
    setSortField('pressureScore');
    setSortOrder('desc');
    setPage(1);
    addToast('Filters reset to default', 'info');
  };

  const handleSort = (field: keyof Player) => {
    if (sortField === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const handleSelectAll = () => {
    if (selectedIds.length === paginatedPlayers.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(paginatedPlayers.map(p => p.id));
    }
  };

  const toggleSelectOne = (id: string) => {
    setSelectedIds(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));
  };

  const handleBulkShortlist = async () => {
    const selectedPlayers = players.filter(p => selectedIds.includes(p.id));
    for (const p of selectedPlayers) {
      await addPlayerToShortlist(p, 'Bulk added from Player Explorer');
    }
    setSelectedIds([]);
  };

  const handleExportCSV = () => {
    const headers = ['ID', 'Player Name', 'Team', 'Role', 'Nationality', 'International Status', 'IPL Experience', 'Pressure Score', 'Sample Size', 'Reliability', 'Eligibility'];
    const rows = players.map(p => [
      p.id,
      p.name,
      p.team,
      p.role,
      p.nationality,
      p.internationalStatus,
      p.iplExperience,
      p.pressureScore ?? 'N/A',
      p.sampleSize,
      p.reliability,
      p.eligibility,
    ]);
    exportToCSV('superr_selector_players_filtered', headers, rows);
    addToast('Exported filtered players to CSV', 'success');
  };

  // Pagination calculation
  const totalPages = Math.ceil(players.length / pageSize) || 1;
  const paginatedPlayers = useMemo(() => {
    const start = (page - 1) * pageSize;
    return players.slice(start, start + pageSize);
  }, [players, page, pageSize]);

  return (
    <div className="space-y-4">
      {/* Search and Filter Panel */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#777F79] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by player name, ID (e.g. p-101), team, speciality..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-[#F7F6F2] text-xs border border-[#E5E8E3] focus:border-[#246B4B] rounded-lg outline-none transition-colors text-[#202522]"
            />
          </div>

          {/* Quick Toolbar */}
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={handleResetFilters}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-[#F7F6F2] hover:bg-stone-200 border border-[#E5E8E3] text-xs font-semibold text-[#202522] transition-colors cursor-pointer"
              title="Reset all filters"
            >
              <RotateCcw className="w-3.5 h-3.5 text-[#777F79]" />
              <span>Reset</span>
            </button>

            <button
              onClick={handleExportCSV}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-[#F7F6F2] hover:bg-stone-200 border border-[#E5E8E3] text-xs font-semibold text-[#202522] transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-[#246B4B]" />
              <span>Export CSV</span>
            </button>

            {/* View Mode Toggle */}
            <div className="flex items-center rounded-lg border border-[#E5E8E3] bg-[#F7F6F2] p-0.5">
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded text-xs transition-colors cursor-pointer ${
                  viewMode === 'table' ? 'bg-white shadow-xs text-[#202522]' : 'text-[#777F79] hover:text-[#202522]'
                }`}
                title="Table View"
              >
                <List className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded text-xs transition-colors cursor-pointer ${
                  viewMode === 'grid' ? 'bg-white shadow-xs text-[#202522]' : 'text-[#777F79] hover:text-[#202522]'
                }`}
                title="Card View"
              >
                <Grid className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Multi-Level Filters Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-2 pt-2 border-t border-[#E5E8E3] text-xs">
          {/* 1. Nationality */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Nationality</label>
            <select
              value={nationality}
              onChange={e => setNationality(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-xs text-[#202522] focus:border-[#246B4B] outline-none"
            >
              <option value="All">All Nationalities</option>
              <option value="Indian">Indian</option>
              <option value="Overseas">Overseas</option>
              <option value="Unknown">Unknown</option>
            </select>
          </div>

          {/* 2. International Status */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Capped Status</label>
            <select
              value={internationalStatus}
              onChange={e => setInternationalStatus(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-xs text-[#202522] focus:border-[#246B4B] outline-none"
            >
              <option value="All">All Statuses</option>
              <option value="Verified Capped">Verified Capped</option>
              <option value="Derived Capped">Derived Capped</option>
              <option value="Uncapped">Uncapped</option>
              <option value="Unknown">Unknown</option>
            </select>
          </div>

          {/* 3. Role */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-xs text-[#202522] focus:border-[#246B4B] outline-none"
            >
              <option value="All">All Roles</option>
              <option value="Batter">Batter</option>
              <option value="Bowler">Bowler</option>
              <option value="All-rounder">All-rounder</option>
              <option value="Wicketkeeper">Wicketkeeper</option>
              <option value="Unknown">Unknown</option>
            </select>
          </div>

          {/* 4. IPL Experience */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">IPL Experience</label>
            <select
              value={iplExperience}
              onChange={e => setIplExperience(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-xs text-[#202522] focus:border-[#246B4B] outline-none"
            >
              <option value="All">All Experience</option>
              <option value="Experienced">Experienced</option>
              <option value="New">New / Emerging</option>
              <option value="Unknown">Unknown</option>
            </select>
          </div>

          {/* 5. Speciality */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Speciality</label>
            <select
              value={speciality}
              onChange={e => setSpeciality(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-xs text-[#202522] focus:border-[#246B4B] outline-none"
            >
              <option value="All">All Specialities</option>
              <option value="Middle-order batter">Middle-order batter</option>
              <option value="Finisher">Finisher</option>
              <option value="Death specialist">Death specialist</option>
              <option value="Powerplay specialist">Powerplay specialist</option>
              <option value="Spin bowler">Spin bowler</option>
              <option value="Pace bowler">Pace bowler</option>
              <option value="Wicketkeeper-batter">Wicketkeeper-batter</option>
              <option value="Bowling all-rounder">Bowling all-rounder</option>
              <option value="Batting all-rounder">Batting all-rounder</option>
            </select>
          </div>

          {/* 6. Pressure Situation */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Pressure Situation</label>
            <select
              value={pressureSituation}
              onChange={e => setPressureSituation(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-xs text-[#202522] focus:border-[#246B4B] outline-none"
            >
              <option value="All">All Situations</option>
              <option value="Chase">Chase</option>
              <option value="Defend">Defend</option>
              <option value="High required run rate">High required run rate</option>
              <option value="Low wickets remaining">Low wickets remaining</option>
              <option value="Powerplay">Powerplay</option>
              <option value="Middle overs">Middle overs</option>
              <option value="Death overs">Death overs</option>
            </select>
          </div>

          {/* 7. Data Eligibility */}
          <div>
            <label className="text-[10px] font-bold text-[#777F79] uppercase block mb-1">Data Eligibility</label>
            <select
              value={eligibility}
              onChange={e => setEligibility(e.target.value as any)}
              className="w-full bg-[#F7F6F2] border border-[#E5E8E3] rounded-md px-2 py-1.5 text-xs text-[#202522] focus:border-[#246B4B] outline-none"
            >
              <option value="All">All Eligibility</option>
              <option value="Eligible">Eligible (≥100 balls)</option>
              <option value="Insufficient sample">Insufficient sample</option>
              <option value="Below data-weight gate">Below data-weight gate</option>
              <option value="Unknown">Unknown</option>
            </select>
          </div>
        </div>

        {/* Filter Stats Bar */}
        <div className="flex flex-wrap items-center justify-between text-xs text-[#777F79] pt-1">
          <div>
            Showing <strong className="text-[#202522]">{matchingCount}</strong> players matching filters (from {totalCount} total; <strong className="text-[#246B4B]">{eligibleCount} eligible</strong>).
          </div>

          {selectedIds.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-[#202522]">{selectedIds.length} selected:</span>
              <button
                onClick={handleBulkShortlist}
                className="px-2.5 py-1 rounded bg-[#246B4B] text-white font-semibold text-xs hover:bg-[#1b533a] cursor-pointer"
              >
                Add Selected to Shortlist
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Results View */}
      {players.length === 0 ? (
        <div className="bg-white rounded-xl border border-[#E5E8E3] p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-[#F7F6F2] text-[#777F79] flex items-center justify-center mx-auto">
            <Filter className="w-6 h-6" />
          </div>
          <h4 className="text-sm font-bold text-[#202522]">No players match your active filters</h4>
          <p className="text-xs text-[#777F79] max-w-md mx-auto">
            Try adjusting your nationality, role, or eligibility criteria, or click Reset Filters to restore the complete candidate pool.
          </p>
          <button
            onClick={handleResetFilters}
            className="px-4 py-2 rounded-lg bg-[#246B4B] text-white text-xs font-semibold hover:bg-[#1b533a] cursor-pointer"
          >
            Reset All Filters
          </button>
        </div>
      ) : viewMode === 'table' ? (
        /* TABLE VIEW */
        <div className="bg-white rounded-xl border border-[#E5E8E3] shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F7F6F2] border-b border-[#E5E8E3] text-[#777F79] uppercase font-bold text-[10px] tracking-wider select-none">
                <tr>
                  <th className="p-3 w-8">
                    <button onClick={handleSelectAll} className="cursor-pointer">
                      {selectedIds.length === paginatedPlayers.length && paginatedPlayers.length > 0 ? (
                        <CheckSquare className="w-4 h-4 text-[#246B4B]" />
                      ) : (
                        <Square className="w-4 h-4 text-gray-400" />
                      )}
                    </button>
                  </th>
                  <th
                    className="p-3 cursor-pointer hover:text-[#202522]"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Player</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="p-3">Role</th>
                  <th className="p-3">Nationality</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Experience</th>
                  <th
                    className="p-3 cursor-pointer hover:text-[#202522]"
                    onClick={() => handleSort('pressureScore')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Pressure Score</span>
                      <ArrowUpDown className="w-3 h-3 text-[#246B4B]" />
                    </div>
                  </th>
                  <th
                    className="p-3 cursor-pointer hover:text-[#202522]"
                    onClick={() => handleSort('sampleSize')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Sample</span>
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="p-3">Reliability</th>
                  <th className="p-3">Data Eligibility</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E8E3]">
                {paginatedPlayers.map(p => {
                  const isSelected = selectedIds.includes(p.id);
                  const isCompared = comparisonPlayerIds.includes(p.id);

                  return (
                    <tr
                      key={p.id}
                      className={`hover:bg-[#F7F6F2]/60 transition-colors ${
                        isSelected ? 'bg-[#EBF7F1]/30' : ''
                      }`}
                    >
                      <td className="p-3">
                        <button
                          onClick={() => toggleSelectOne(p.id)}
                          className="cursor-pointer"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-[#246B4B]" />
                          ) : (
                            <Square className="w-4 h-4 text-gray-300" />
                          )}
                        </button>
                      </td>
                      <td className="p-3">
                        <div
                          className="font-bold text-[#202522] hover:text-[#246B4B] cursor-pointer flex items-center space-x-2"
                          onClick={() => openPlayerProfile(p)}
                        >
                          <span>{p.name}</span>
                          {p.designation === 'Captain' && (
                            <span className="text-[9px] bg-amber-500 text-white font-bold px-1 rounded">
                              CPT
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-[#777F79]">{p.team}</span>
                      </td>
                      <td className="p-3">
                        <span className="font-medium text-[#202522]">{p.role}</span>
                        <span className="text-[10px] text-[#777F79] block">{p.speciality}</span>
                      </td>
                      <td className="p-3">
                        <span className="text-[#202522]">{p.nationality}</span>
                      </td>
                      <td className="p-3">
                        <StatusBadge status={p.internationalStatus} />
                      </td>
                      <td className="p-3 text-[#777F79]">
                        {p.iplExperience}
                      </td>
                      <td className="p-3 font-mono">
                        {p.pressureScore !== null ? (
                          <div className="flex items-baseline space-x-1">
                            <span className="font-bold text-sm text-[#246B4B]">
                              {formatScore(p.pressureScore)}
                            </span>
                            <span className="text-[10px] text-[#777F79]">/ 100</span>
                          </div>
                        ) : (
                          <span className="text-[#777F79] italic">N/A</span>
                        )}
                      </td>
                      <td className="p-3 font-mono text-[#202522]">
                        {p.sampleSize} balls
                        <span className="text-[10px] text-[#777F79] block">{p.matches} matches</span>
                      </td>
                      <td className="p-3">
                        <StatusBadge status={p.reliability} />
                      </td>
                      <td className="p-3">
                        <StatusBadge status={p.eligibility} />
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            onClick={() => addToComparison(p.id)}
                            disabled={isCompared}
                            title={isCompared ? 'In comparison' : 'Compare player'}
                            className={`p-1.5 rounded transition-colors cursor-pointer ${
                              isCompared
                                ? 'bg-stone-100 text-stone-300 cursor-not-allowed'
                                : 'hover:bg-stone-200 text-[#777F79] hover:text-[#202522]'
                            }`}
                          >
                            <Scale className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => addPlayerToShortlist(p)}
                            title="Add to shortlist"
                            className="p-1.5 rounded hover:bg-stone-200 text-[#777F79] hover:text-[#246B4B] transition-colors cursor-pointer"
                          >
                            <BookmarkPlus className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => openPlayerProfile(p)}
                            title="Inspect Profile"
                            className="p-1.5 rounded bg-[#F7F6F2] hover:bg-stone-200 text-[#246B4B] transition-colors cursor-pointer"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Table Pagination Bar */}
          <div className="p-3 bg-[#F7F6F2] border-t border-[#E5E8E3] flex flex-col sm:flex-row items-center justify-between text-xs text-[#777F79] gap-2">
            <div className="flex items-center space-x-2">
              <span>Show</span>
              <select
                value={pageSize}
                onChange={e => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="bg-white border border-[#E5E8E3] rounded px-2 py-1 text-xs text-[#202522] outline-none"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
              <span>per page (Page {page} of {totalPages})</span>
            </div>

            <div className="flex items-center space-x-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage(prev => Math.max(1, prev - 1))}
                className="px-3 py-1 rounded bg-white border border-[#E5E8E3] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-stone-100 font-medium cursor-pointer"
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                className="px-3 py-1 rounded bg-white border border-[#E5E8E3] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-stone-100 font-medium cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* GRID / CARD VIEW */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {paginatedPlayers.map(p => {
            const isCompared = comparisonPlayerIds.includes(p.id);

            return (
              <div
                key={p.id}
                className="bg-white rounded-xl border border-[#E5E8E3] p-4 shadow-xs hover:border-gray-300 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-[#202522] text-white flex items-center justify-center font-bold text-sm shrink-0">
                        {p.name.charAt(0)}
                      </div>
                      <div>
                        <h4
                          onClick={() => openPlayerProfile(p)}
                          className="font-bold text-sm text-[#202522] hover:text-[#246B4B] cursor-pointer"
                        >
                          {p.name}
                        </h4>
                        <span className="text-[11px] text-[#777F79]">{p.team}</span>
                      </div>
                    </div>
                    <StatusBadge status={p.internationalStatus} />
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs py-2 border-y border-[#F0F2EE]">
                    <div>
                      <span className="text-[10px] text-[#777F79] block">Role & Speciality</span>
                      <strong className="text-[#202522] truncate block">{p.role}</strong>
                      <span className="text-[10px] text-[#777F79] truncate block">{p.speciality}</span>
                    </div>

                    <div>
                      <span className="text-[10px] text-[#777F79] block">Pressure Score</span>
                      {p.pressureScore !== null ? (
                        <span className="text-base font-black text-[#246B4B]">
                          {formatScore(p.pressureScore)}
                        </span>
                      ) : (
                        <span className="text-[#777F79] italic">N/A</span>
                      )}
                    </div>
                  </div>

                  <div className="mt-2.5 flex items-center justify-between text-[11px] text-[#777F79]">
                    <span>Sample: <strong className="text-[#202522]">{p.sampleSize}</strong> balls</span>
                    <span>Reliability: <StatusBadge status={p.reliability} /></span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-[#E5E8E3] flex items-center justify-between gap-1.5">
                  <button
                    onClick={() => addToComparison(p.id)}
                    disabled={isCompared}
                    className={`flex-1 py-1.5 rounded text-xs font-semibold border transition-colors cursor-pointer flex items-center justify-center space-x-1 ${
                      isCompared
                        ? 'bg-stone-100 text-stone-300 border-stone-200 cursor-not-allowed'
                        : 'bg-white hover:bg-[#F7F6F2] text-[#202522] border-[#E5E8E3]'
                    }`}
                  >
                    <Scale className="w-3 h-3" />
                    <span>Compare</span>
                  </button>

                  <button
                    onClick={() => addPlayerToShortlist(p)}
                    className="p-1.5 rounded bg-white hover:bg-[#F7F6F2] text-[#777F79] hover:text-[#246B4B] border border-[#E5E8E3] transition-colors cursor-pointer"
                    title="Shortlist"
                  >
                    <BookmarkPlus className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => openPlayerProfile(p)}
                    className="flex-1 py-1.5 rounded text-xs font-semibold bg-[#246B4B] hover:bg-[#1b533a] text-white transition-colors cursor-pointer flex items-center justify-center space-x-1 shadow-xs"
                  >
                    <Eye className="w-3 h-3" />
                    <span>Profile</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

