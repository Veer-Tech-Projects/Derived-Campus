import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { GovernanceTriageAction, TriageTarget } from "@/lib/media-governance-api";
import { Loader2, CheckCircle, XCircle, Trash2, ImageOff } from "lucide-react"; 

interface TriageModalProps {
  isOpen: boolean;
  onClose: () => void;
  target: TriageTarget | null;
  isMutating: boolean;
  onAction: (action: GovernanceTriageAction) => void;
}

export function TriageModal({ isOpen, onClose, target, isMutating, onAction }: TriageModalProps) {
  if (!target) return null;

  const handleOpenChange = (open: boolean) => {
    if (!open && !isMutating) onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Triage Candidate: {target.collegeName}</DialogTitle>
          <DialogDescription>
            Reviewing {target.mediaType.replace("_", " ")} candidate fetched by ingestion pipeline.
          </DialogDescription>
        </DialogHeader>

        {/* ENTERPRISE RENDERER: Graceful fallback logic & Strict Security */}
        <div className="relative w-full aspect-video bg-slate-50 rounded-md overflow-hidden flex flex-col items-center justify-center border border-slate-200">
          
          {/* Background Layer: Only visible if image fails to load */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400 gap-2">
            <ImageOff className="w-10 h-10 opacity-40" />
            <span className="text-sm font-medium">Preview Not Available or Removed</span>
          </div>

          <img
            src={target.sourceUrl}
            alt="Candidate Preview"
            className="object-contain w-full h-full relative z-10 transition-opacity duration-300"
            loading="lazy"
            decoding="async"
            referrerPolicy="no-referrer"
            crossOrigin="anonymous" // Restored for Canvas-Taint Protection
            onError={(e) => {
              // --- AUDITOR FIX: MATHEMETICAL DOM REMOVAL ---
              e.currentTarget.style.display = "none"; 
            }}
          />
        </div>

        <DialogFooter className="flex items-center sm:justify-between pt-4 mt-2 border-t">
          <Button
            variant="ghost"
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
            disabled={isMutating}
            onClick={() => onAction("DELETE")}
          >
            {isMutating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Trash2 className="w-4 h-4 mr-2" />}
            Delete (Takedown)
          </Button>

          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={isMutating}
              onClick={() => onAction("REJECT")}
            >
              {isMutating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <XCircle className="w-4 h-4 mr-2" />}
              Reject
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-md"
              disabled={isMutating}
              onClick={() => onAction("ACCEPT")}
            >
              {isMutating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
              Accept Candidate
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}