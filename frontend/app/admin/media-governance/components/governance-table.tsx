import { GovernanceCollege, GovernanceMediaType, TriageTarget } from "@/lib/media-governance-api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "./status-badge";
import { Play, Eye, RotateCcw } from "lucide-react";

interface GovernanceTableProps {
  data: GovernanceCollege[];
  isLoading: boolean;
  isMutating: boolean;
  skip: number;
  limit: number;
  totalCount: number;
  selectedIds: string[];
  onSelect: (id: string) => void;
  onSelectAll: () => void;
  onNext: () => void;
  onPrev: () => void;
  onDispatch: (collegeId: string, mediaType: GovernanceMediaType, force: boolean) => void;
  onOpenTriage: (target: TriageTarget) => void;
}

export function GovernanceTable({
  data, isLoading, isMutating, skip, limit, totalCount, 
  selectedIds, onSelect, onSelectAll,
  onNext, onPrev, onDispatch, onOpenTriage
}: GovernanceTableProps) {
  
  const renderActionCell = (college: GovernanceCollege, mediaType: GovernanceMediaType) => {
    const detail = college.media_details?.[mediaType];
    
    if (!detail) return <StatusBadge status={null} />;

    if (detail.status === "PENDING" || detail.status === "ACCEPTED") {
      return (
        <div className="flex items-center justify-between min-w-[160px]">
          <StatusBadge status={detail.status} isExhausted={detail.exhausted} />
          <Button
            size="sm"
            variant="ghost"
            disabled={isMutating}
            className="text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50"
            onClick={() => onOpenTriage({
              collegeId: college.college_id,
              collegeName: college.canonical_name,
              mediaId: detail.media_id!,
              mediaType: mediaType,
              sourceUrl: detail.source_url!
            })}
          >
            <Eye className="w-4 h-4 mr-1" /> Triage
          </Button>
        </div>
      );
    }

    if (detail.exhausted) {
      return (
        <div className="flex items-center justify-between min-w-[160px]">
          <StatusBadge status={detail.status} isExhausted={detail.exhausted} />
          <Button size="sm" variant="destructive" disabled={isMutating} onClick={() => onDispatch(college.college_id, mediaType, true)}>
            <RotateCcw className="w-4 h-4 mr-1" /> Force
          </Button>
        </div>
      );
    }

    return (
      <div className="flex items-center justify-between min-w-[160px]">
        <StatusBadge status={detail.status} isExhausted={false} />
        <Button size="sm" variant="outline" disabled={isMutating} onClick={() => onDispatch(college.college_id, mediaType, false)}>
          <Play className="w-4 h-4 mr-1" /> Ingest
        </Button>
      </div>
    );
  };

  const allSelected = data.length > 0 && selectedIds.length === data.length;

  return (
    <div className="space-y-4">
      <div className="border border-slate-200 rounded-xl bg-white shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-slate-50 border-b border-slate-200">
            <TableRow>
              <TableHead className="w-[4%] text-center">
                <input 
                  type="checkbox" 
                  checked={allSelected} 
                  onChange={onSelectAll}
                  disabled={isLoading || isMutating || data.length === 0}
                  className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600 cursor-pointer"
                />
              </TableHead>
              <TableHead className="w-[6%] font-semibold text-slate-600">Sr. No</TableHead>
              <TableHead className="w-[30%] font-semibold text-slate-600">Registry Entity</TableHead>
              <TableHead className="w-[30%] font-semibold text-slate-600">Primary Logo</TableHead>
              <TableHead className="w-[30%] font-semibold text-slate-600">Campus Hero</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-100">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-4 rounded" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                  <TableCell><Skeleton className="h-6 w-3/4" /></TableCell>
                  <TableCell><Skeleton className="h-8 w-full" /></TableCell>
                  <TableCell><Skeleton className="h-8 w-full" /></TableCell>
                </TableRow>
              ))
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-16 text-slate-500 font-medium">
                  No registry entities found matching current filters.
                </TableCell>
              </TableRow>
            ) : (
              data.map((college, index) => (
                <TableRow key={college.college_id} className="hover:bg-slate-50/50 transition-colors">
                  <TableCell className="text-center">
                    <input 
                      type="checkbox" 
                      checked={selectedIds.includes(college.college_id)} 
                      onChange={() => onSelect(college.college_id)}
                      disabled={isMutating}
                      className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600 cursor-pointer"
                    />
                  </TableCell>
                  <TableCell className="text-slate-400 font-mono text-xs">
                    {(skip + index + 1).toString().padStart(3, '0')}
                  </TableCell>
                  <TableCell>
                    <div className="font-bold text-slate-900">{college.canonical_name}</div>
                    <div className="text-xs text-slate-500 font-medium mt-0.5">{college.city || "Unknown Location"}</div>
                  </TableCell>
                  <TableCell>{renderActionCell(college, "LOGO")}</TableCell>
                  <TableCell>{renderActionCell(college, "CAMPUS_HERO")}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-500 px-2 font-medium">
        <div>
          Showing {totalCount === 0 ? 0 : skip + 1} to {Math.min(skip + limit, totalCount)} of {totalCount} entries
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={skip === 0 || isMutating || isLoading} onClick={onPrev}>
            Previous
          </Button>
          <Button variant="outline" size="sm" disabled={skip + limit >= totalCount || isMutating || isLoading} onClick={onNext}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}