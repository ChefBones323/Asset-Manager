import type { SocialPostPayload } from "@/interfaces/socialPost";

export interface SocialConnector {
  platform: string;
  publish(payload: SocialPostPayload): Promise<ConnectorResult>;
}

export interface ConnectorResult {
  success: boolean;
  platform: string;
  postId?: string;
  error?: string;
  timestamp: string;
}

const registry = new Map<string, SocialConnector>();

export function registerConnector(connector: SocialConnector): void {
  registry.set(connector.platform, connector);
}

export function getConnector(platform: string): SocialConnector | undefined {
  return registry.get(platform);
}

export function getAllConnectors(): SocialConnector[] {
  return Array.from(registry.values());
}

export function getRegisteredPlatforms(): string[] {
  return Array.from(registry.keys());
}
