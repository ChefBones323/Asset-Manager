import { useEventStore, type PlatformEvent } from "@/store/eventStore";
import { dispatchToAllPlatforms, type DispatchResult } from "@/services/integrations/publishDispatcher";
import type { SocialPostPayload } from "@/interfaces/socialPost";

const EVENT_TYPE_MAP: Record<string, string> = {
  facebook: "facebook_post_sent",
  twitter: "twitter_post_sent",
  linkedin: "linkedin_post_sent",
  instagram: "instagram_post_sent",
  youtube: "youtube_post_sent",
  reddit: "reddit_post_sent",
  discord: "discord_message_sent",
};

const processedEventIds = new Set<string>();
let unsubscribe: (() => void) | null = null;

function emitPublishEvent(
  platform: string,
  success: boolean,
  contentEventId: string,
  postId?: string,
  error?: string
): void {
  const eventType = success
    ? EVENT_TYPE_MAP[platform] || `${platform}_post_sent`
    : "platform_publish_failed";

  const event: PlatformEvent = {
    event_id: `evt-pub-${platform}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    domain: "content",
    event_type: eventType,
    actor_id: "social-publisher-worker",
    payload: {
      platform,
      source_event_id: contentEventId,
      success,
      ...(postId && { platform_post_id: postId }),
      ...(error && { error }),
    },
    timestamp: new Date().toISOString(),
  };

  useEventStore.getState().pushEvent(event);
}

async function handleContentCreated(event: PlatformEvent): Promise<void> {
  if (processedEventIds.has(event.event_id)) return;
  processedEventIds.add(event.event_id);

  const platforms = event.payload.platforms as string[] | undefined;
  if (!platforms || !Array.isArray(platforms) || platforms.length === 0) return;

  const externalPlatforms = platforms.filter((p) => p !== "civic");
  if (externalPlatforms.length === 0) return;

  const payload: SocialPostPayload = {
    content: (event.payload.content as string) || "",
    platforms: externalPlatforms,
    ...(event.payload.media && { media: event.payload.media as string[] }),
    ...(event.payload.tags && { tags: event.payload.tags as string[] }),
  };

  const results: DispatchResult[] = await dispatchToAllPlatforms(payload);

  for (const { platform, result } of results) {
    emitPublishEvent(
      platform,
      result.success,
      event.event_id,
      result.postId,
      result.error
    );
  }
}

function processEvents(): void {
  const events = useEventStore.getState().events;
  for (const event of events) {
    if (
      event.event_type === "content_created" &&
      event.domain === "content" &&
      !processedEventIds.has(event.event_id)
    ) {
      handleContentCreated(event);
    }
  }
}

export function startSocialPublisherWorker(): void {
  if (unsubscribe) return;

  unsubscribe = useEventStore.subscribe(processEvents);
}

export function stopSocialPublisherWorker(): void {
  if (unsubscribe) {
    unsubscribe();
    unsubscribe = null;
  }
}
