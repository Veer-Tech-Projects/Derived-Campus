import {
  BandResultDTO,
  CollegeBand,
  CollegeFilterSearchResponse,
} from "../types/contracts";

export const BAND_PRIORITY: CollegeBand[] = [
  "SAFE",
  "MODERATE",
  "HARD",
  "SUGGESTED",
];

export function getBandResult(
  response: CollegeFilterSearchResponse,
  band: CollegeBand
): BandResultDTO {
  switch (band) {
    case "SAFE":
      return response.bands.safe;
    case "MODERATE":
      return response.bands.moderate;
    case "HARD":
      return response.bands.hard;
    case "SUGGESTED":
      return response.bands.suggested;
  }
}

export function getBandCount(
  response: CollegeFilterSearchResponse,
  band: CollegeBand
): number {
  switch (band) {
    case "SAFE":
      return response.band_counts.safe;
    case "MODERATE":
      return response.band_counts.moderate;
    case "HARD":
      return response.band_counts.hard;
    case "SUGGESTED":
      return response.band_counts.suggested;
  }
}

export function getDefaultVisibleBand(
  response: CollegeFilterSearchResponse,
  allowedBands?: CollegeBand[]
): CollegeBand {
  const candidates = allowedBands?.length ? allowedBands : BAND_PRIORITY;

  for (const band of BAND_PRIORITY) {
    if (!candidates.includes(band)) continue;
    if (getBandCount(response, band) > 0) return band;
  }

  return candidates[0] ?? "SAFE";
}