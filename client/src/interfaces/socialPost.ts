export interface SocialPostPayload {
  content: string;
  media?: string[];
  tags?: string[];
  platforms: string[];
}

export const SUPPORTED_PLATFORMS = [
  { id: "civic", label: "Civic Feed", default: true },
  { id: "facebook", label: "Facebook", default: false },
  { id: "twitter", label: "X (Twitter)", default: false },
  { id: "linkedin", label: "LinkedIn", default: false },
  { id: "instagram", label: "Instagram", default: false },
  { id: "youtube", label: "YouTube", default: false },
  { id: "reddit", label: "Reddit", default: false },
  { id: "discord", label: "Discord", default: false },
] as const;

export type PlatformId = typeof SUPPORTED_PLATFORMS[number]["id"];
