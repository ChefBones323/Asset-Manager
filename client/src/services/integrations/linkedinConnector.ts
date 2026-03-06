import type { SocialConnector, ConnectorResult } from "./connectorRegistry";
import { registerConnector } from "./connectorRegistry";
import type { SocialPostPayload } from "@/interfaces/socialPost";

const linkedinConnector: SocialConnector = {
  platform: "linkedin",
  async publish(payload: SocialPostPayload): Promise<ConnectorResult> {
    const timestamp = new Date().toISOString();
    try {
      await new Promise((resolve) => setTimeout(resolve, 900 + Math.random() * 500));
      return {
        success: true,
        platform: "linkedin",
        postId: `li_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        timestamp,
      };
    } catch (err) {
      return {
        success: false,
        platform: "linkedin",
        error: err instanceof Error ? err.message : "Unknown error",
        timestamp,
      };
    }
  },
};

registerConnector(linkedinConnector);
export default linkedinConnector;
