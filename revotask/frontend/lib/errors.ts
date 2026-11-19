export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getErrorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong";
}
