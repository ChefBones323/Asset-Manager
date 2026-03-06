import type { SocialConnector, ConnectorResult } from "./connectorRegistry";
import { registerConnector } from "./connectorRegistry";
import type { SocialPostPayload } from "@/interfaces/socialPost";

const twitterConnector: SocialConnector = {
  platform: "twitter",
  async publish(payload: SocialPostPayload): Promise<ConnectorResult> {
    const timestamp = new Date().toISOString();
    try {
      await new Promise((resolve) => setTimeout(resolve, 600 + Math.random() * 300));
      return {
        success: true,
        platform: "twitter",
        postId: `tw_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        timestamp,
      };
    } catch (err) {
      return {
        success: false,
        platform: "twitter",
        error: err instanceof Error ? err.message : "Unknown error",
        timestamp,
      };
    }
  },
};

registerConnector(twitterConnector);
export default twitterConnector;
