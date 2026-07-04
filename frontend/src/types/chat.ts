export type MessageRole = "user" | "assistant" | "system";

export type MessageStatus = "idle" | "streaming" | "completed" | "failed";

export type DisplayType = "text" | "weather" | "itinerary" | "travel";

export type ToolStatus = "running" | "success" | "failed" | "fallback";

export interface ToolInvocation {
  id: string;
  name: "weather" | "map" | "rag" | string;
  label?: string;
  status: ToolStatus;
  message?: string;
}

export interface TaskPlanStep {
  step: string;
  tool: string;
  reason: string;
}

export interface ToolUsage {
  tool: string;
  status: "success" | "failed" | "fallback" | string;
  summary: string;
}

export interface RetrievedChunk {
  chunk_id?: string;
  title?: string;
  city?: string;
  category?: string;
  score?: number;
  content_preview?: string;
}

export interface RagSource {
  id?: string;
  title?: string;
  city?: string;
  country?: string;
  category?: string;
  content?: string;
  source_url?: string;
  source?: string;
  score?: number;
  url?: string;
  metadata?: Record<string, unknown>;
}

export interface WeatherData {
  city: string;
  date?: string;
  provider?: string;
  condition?: string;
  temperature?: number;
  temp?: number;
  current_temperature?: number;
  temp_min?: number;
  temp_max?: number;
  humidity?: number;
  wind?: string;
  precipitationProbability?: number;
  rain_probability?: number;
  travel_advice?: string;
  summary?: string;
  forecast?: Array<{
    date?: string;
    condition?: string;
    temp_min?: number;
    temp_max?: number;
    rain_probability?: number;
    wind?: string;
  }>;
}

export interface ItineraryStop {
  time?: string;
  title: string;
  name?: string;
  description?: string;
  location?: string;
  address?: string;
  type?: string;
  lat?: number;
  lng?: number;
  latitude?: number;
  longitude?: number;
}

export interface ItineraryDay {
  day: string;
  title?: string;
  theme?: string;
  pace?: string;
  stops: ItineraryStop[];
  routes?: Array<{
    from?: string;
    to?: string;
    path?: Array<[number, number]>;
    distance_m?: number;
    duration_min?: number;
    mode?: string;
  }>;
  notes?: string;
}

export interface FoodRecommendation {
  name: string;
  reason?: string;
  area?: string;
  tags?: string[];
}

export interface TravelTip {
  title: string;
  content: string;
}

export interface MessageMetadata {
  weatherData?: WeatherData;
  itinerary?: ItineraryDay[];
  foodRecommendations?: FoodRecommendation[];
  tips?: TravelTip[];
  city?: string;
  intent?: string;
  selectedTool?: string;
  confidence?: number;
  cards?: unknown[];
  taskPlan?: TaskPlanStep[];
  toolsUsed?: ToolUsage[];
  retrievedChunks?: RetrievedChunk[];
  traceMetadata?: Record<string, unknown>;
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

export interface ConversationHistory {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: number;
}
