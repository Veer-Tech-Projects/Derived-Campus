import { Badge } from "@/components/ui/badge";
import { AlertOctagon } from "lucide-react";
import { GovernanceDerivedState, GovernanceMediaStatus } from "@/lib/media-governance-api";

interface StatusBadgeProps {
  status: GovernanceMediaStatus | GovernanceDerivedState | null;
  isExhausted?: boolean;
}

export function StatusBadge({ status, isExhausted }: StatusBadgeProps) {
  if (isExhausted) {
    return (
      <Badge variant="outline" className="border-red-500 text-red-700 bg-red-50 gap-1.5 pr-2.5 shadow-sm">
        <AlertOctagon className="w-3 h-3" />
        EXHAUSTED
      </Badge>
    );
  }

  switch (status) {
    case "ACCEPTED":
      return (
        <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border-emerald-200 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span> Accepted
        </Badge>
      );
    case "PENDING":
      return (
        <Badge className="bg-amber-50 text-amber-700 hover:bg-amber-100 border-amber-200 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5"></span> Pending
        </Badge>
      );
    case "REJECTED":
      return (
        <Badge className="bg-orange-50 text-orange-700 hover:bg-orange-100 border-orange-200 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-orange-500 mr-1.5"></span> Rejected
        </Badge>
      );
    case "DELETED":
    case "GRAVEYARD":
      return (
        <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-200 border-slate-200 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mr-1.5"></span> Graveyard
        </Badge>
      );
    case "EMPTY":
    case null:
    default:
      return (
        <Badge variant="outline" className="text-slate-400 border-slate-200 shadow-sm bg-white">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-200 mr-1.5"></span> Empty
        </Badge>
      );
  }
}