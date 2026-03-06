import type { SocialPostPayload } from "@/interfaces/socialPost";
import { getConnector, type ConnectorResult } from "./connectorRegistry";

import "./facebookConnector";
import "./twitterConnector";
import "./linkedinConnector";
import "./instagramConnector";
import "./youtubeConnector";
import "./redditConnector";
import "./discordConnector";

export interface DispatchResult {
  platform: string;
  result: ConnectorResult;
}

export async function dispatchToAllPlatforms(
  payload: SocialPostPayload
): Promise<DispatchResult[]> {
  const results: DispatchResult[] = [];

  for (const platform of payload.platforms) {
    if (platform === "civic") continue;

    const connector = getConnector(platform);
    if (!connector) {
      results.push({
        platform,
        result: {
          success: false,
          platform,
          error: `No connector registered for platform: ${platform}`,
          timestamp: new Date().toISOString(),
        },
      });
      continue;
    }

    const result = await connector.publish(payload);
    results.push({ platform, result });
  }

  return results;
}

export async function dispatchToPlatform(
  platform: string,
  payload: SocialPostPayload
): Promise<ConnectorResult> {
  const connector = getConnector(platform);
  if (!connector) {
    return {
      success: false,
      platform,
      error: `No connector registered for platform: ${platform}`,
      timestamp: new Date().toISOString(),
    };
  }
  return connector.publish(payload);
}
