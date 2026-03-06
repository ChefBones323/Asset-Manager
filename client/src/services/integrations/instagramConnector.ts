import type { SocialConnector, ConnectorResult } from "./connectorRegistry";
import { registerConnector } from "./connectorRegistry";
import type { SocialPostPayload } from "@/interfaces/socialPost";

const instagramConnector: SocialConnector = {
  platform: "instagram",
  async publish(payload: SocialPostPayload): Promise<ConnectorResult> {
    const timestamp = new Date().toISOString();
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000 + Math.random() * 500));
      return {
        success: true,
        platform: "instagram",
        postId: `ig_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        timestamp,
      };
    } catch (err) {
      return {
        success: false,
        platform: "instagram",
        error: err instanceof Error ? err.message : "Unknown error",
        timestamp,
      };
    }
  },
};

registerConnector(instagramConnector);
export default instagramConnector;
