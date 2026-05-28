import type { AssistantMessage, Message } from "../messages";
import type { Tool } from "../tools";

export interface ModelProviderInvokeParams {
  model: string;
  messages: Message[];
  tools?: Tool[];
  options?: Record<string, unknown>;
  signal?: AbortSignal;
}

/**
 * A provider for a model.
 */
export interface ModelProvider {
  /**
   * Invokes the model with the given messages and options.
   * @param params - The parameters for the invocation.
   * @returns The complete response from the model.
   */
  invoke(
    // eslint-disable-next-line no-unused-vars
    params: ModelProviderInvokeParams,
  ): Promise<AssistantMessage>;

  /**
   * Streams the model response, yielding accumulated snapshots.
   * Each yielded value is a progressively more complete {@link AssistantMessage}.
   * The final yielded value is equivalent to what {@link invoke} would return.
   * @param params - The parameters for the invocation (same as {@link invoke}).
   */
  stream(
    // eslint-disable-next-line no-unused-vars
    params: ModelProviderInvokeParams,
  ): AsyncGenerator<AssistantMessage>;
}
