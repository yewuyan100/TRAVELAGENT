export type MessageRole = "user" | "assistant" | "system";

export type MessageStatus = "idle" | "streaming" | "completed" | "failed";

export type DisplayType = "text" | "weather" | "itinerary" | "travel";

export type ToolStatus = "running" | "success" | "failed";

export interface ToolInvocation {
  id: string;
  name: "weather" | "map" | "rag" | string;
  label?: string;
  status: ToolStatus;
  message?: string;
}

export interface RagSource {
  id?: string;
  title: string;
  source?: string;
  score?: number;
  url?: string;
  metadata?: Record<string, unknown>;
}

export interface WeatherData {
  city: string;
  condition?: string;
  temperature?: number;
  temp?: number;
  humidity?: number;
  wind?: string;
  precipitationProbability?: number;
}

export interface ItineraryStop {
  time?: string;
  title: string;
  description?: string;
  location?: string;
}

export interface ItineraryDay {
  day: string;
  title?: string;
  stops: ItineraryStop[];
}

export interface MessageMetadata {
  weatherData?: WeatherData;
  itinerary?: ItineraryDay[];
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status?: MessageStatus;
  displayType?: DisplayType;
  toolInvocations?: ToolInvocation[];
  ragSources?: RagSource[];
  metadata?: MessageMetadata;
  error?: string;
  createdAt: number;
}
