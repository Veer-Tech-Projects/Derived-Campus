import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GovernanceLocation, LocationTriageAction } from "@/lib/location-governance-api";
import { AlertTriangle, MapPin, CheckCircle2, XCircle, Trash2, Globe } from "lucide-react";
import { toast } from "sonner";

interface Props {
  college: GovernanceLocation | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (
    collegeId: string, 
    action: LocationTriageAction, 
    candidateId?: string | null, 
    overrides?: { city?: string; district?: string; state_code?: string; pincode?: string }
  ) => Promise<void>;
}

export function LocationTriageModal({ college, isOpen, onClose, onConfirm }: Props) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [stateCode, setStateCode] = useState("");
  const [pincode, setPincode] = useState("");

  useEffect(() => {
    if (college?.candidate_details) {
      setCity(college.candidate_details.parsed_city || "");
      setDistrict(college.candidate_details.parsed_district || "");
      setStateCode(college.candidate_details.parsed_state_code || "");
      setPincode(college.candidate_details.pincode || "");
    } else {
      setCity("");
      setDistrict("");
      setStateCode("");
      setPincode("");
    }
  }, [college]);

  if (!college) return null;
  const cand = college.candidate_details;

  const handleAction = async (action: LocationTriageAction) => {
    if ((action === "ACCEPT" || action === "REJECT") && !cand?.candidate_id) {
      toast.error("Candidate ID missing. Cannot perform triage.");
      return;
    }

    setIsSubmitting(true);
    try {
      const overrides = action === "ACCEPT" ? { city, district, state_code: stateCode, pincode } : undefined;
      await onConfirm(college.college_id, action, cand?.candidate_id, overrides);
    } finally {
      setIsSubmitting(false);
    }
  };

  // [AUDIT FIX] Strict mathematical coordinate validation (ignores 0 truthiness bugs)
  const hasValidCoordinates = cand?.latitude !== null && cand?.latitude !== undefined && cand?.longitude !== null && cand?.longitude !== undefined;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[800px] bg-slate-50/50">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <MapPin className="w-5 h-5 text-teal-600" />
            Resolve Location Candidate
          </DialogTitle>
          <div className="text-sm text-zinc-500 font-medium pt-1">
            {college.canonical_name}
          </div>
        </DialogHeader>

        <div className="py-2 space-y-4">
          {cand ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              <div className="space-y-4">
                <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Google Places Payload</h4>
                  <p className="text-xs font-medium text-slate-800 mb-2 leading-relaxed">{cand.raw_address}</p>
                  <div className="flex gap-3 text-[10px] text-slate-500 font-mono bg-slate-50 p-1.5 rounded">
                    <span>Lat: {cand.latitude}</span>
                    <span>Lng: {cand.longitude}</span>
                  </div>
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm space-y-3">
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Parsed Geometry (Editable)</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[10px] font-semibold text-slate-600">Pincode</label>
                      <Input value={pincode} onChange={(e) => setPincode(e.target.value)} disabled={isSubmitting} className="font-mono text-xs h-8" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-semibold text-slate-600">State Code</label>
                      <Input value={stateCode} onChange={(e) => setStateCode(e.target.value)} disabled={isSubmitting} className="font-mono text-xs h-8" />
                    </div>
                    <div className="space-y-1 col-span-2">
                      <label className="text-[10px] font-semibold text-slate-600">District</label>
                      <Input value={district} onChange={(e) => setDistrict(e.target.value)} disabled={isSubmitting} className="text-xs h-8" />
                    </div>
                    <div className="space-y-1 col-span-2">
                      <label className="text-[10px] font-semibold text-slate-600">City</label>
                      <Input value={city} onChange={(e) => setCity(e.target.value)} disabled={isSubmitting} className="text-xs h-8" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-lg p-1.5 shadow-sm h-full min-h-[300px] flex flex-col">
                <div className="flex items-center gap-2 px-2 pb-2 pt-1 border-b border-slate-100">
                  <Globe className="w-3 h-3 text-slate-400" />
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Live Coordinate Verification</span>
                </div>
                <div className="flex-grow w-full bg-slate-100 rounded-md overflow-hidden relative mt-1.5">
                  {hasValidCoordinates ? (
                    <iframe 
                      width="100%" 
                      height="100%" 
                      style={{ border: 0 }} 
                      loading="lazy" 
                      allowFullScreen 
                      referrerPolicy="no-referrer-when-downgrade" 
                      src={`https://maps.google.com/maps?q=${cand.latitude},${cand.longitude}&t=m&z=15&output=embed`}
                    ></iframe>
                  ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400">
                      <Globe className="w-8 h-8 mb-2 opacity-50" />
                      <span className="text-xs font-medium">No Coordinates Available</span>
                    </div>
                  )}
                </div>
              </div>

            </div>
          ) : (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2 text-sm border border-red-100">
              <AlertTriangle className="w-4 h-4" />
              No pending candidate available in the airlock.
            </div>
          )}
        </div>

        <DialogFooter className="flex justify-between items-center sm:justify-between border-t border-slate-200 pt-4 mt-2">
          <Button 
            variant="destructive" 
            size="sm"
            onClick={() => handleAction("DELETE")} 
            disabled={isSubmitting}
            className="bg-rose-100 text-rose-700 hover:bg-rose-200 shadow-none border-none"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete Canonical
          </Button>

          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => handleAction("REJECT")} 
              disabled={isSubmitting || !cand}
              className="hover:bg-amber-50 hover:text-amber-700 hover:border-amber-200 bg-white"
            >
              <XCircle className="w-4 h-4 mr-2" />
              Reject Candidate
            </Button>
            <Button 
              size="sm"
              onClick={() => handleAction("ACCEPT")} 
              disabled={isSubmitting || !cand}
              className="bg-teal-600 hover:bg-teal-700 text-white shadow-md"
            >
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Approve Coordinates
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}