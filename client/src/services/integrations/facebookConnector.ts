import type { SocialConnector, ConnectorResult } from "./connectorRegistry";
import { registerConnector } from "./connectorRegistry";
import type { SocialPostPayload } from "@/interfaces/socialPost";

const facebookConnector: SocialConnector = {
  platform: "facebook",
  async publish(payload: SocialPostPayload): Promise<ConnectorResult> {
    const timestamp = new Date().toISOString();
    try {
      await new Promise((resolve) => setTimeout(resolve, 800 + Math.random() * 400));
      return {
        success: true,
        platform: "facebook",
        postId: `fb_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        timestamp,
      };
    } catch (err) {
      return {
        success: false,
        platform: "facebook",
        error: err instanceof Error ? err.message : "Unknown error",
        timestamp,
      };
    }
  },
};

registerConnector(facebookConnector);
export default facebookConnector;
