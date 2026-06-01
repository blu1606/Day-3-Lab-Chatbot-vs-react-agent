import { NextResponse } from "next/server";

const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const payload = await request.json();

  try {
    const response = await fetch(`${FASTAPI_BASE_URL}/api/v1/diagnose`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const contentType = response.headers.get("content-type") ?? "";
    const data = contentType.includes("application/json")
      ? await response.json()
      : {
          error_code: "DIAGNOSE_BACKEND_NON_JSON_RESPONSE",
          message: await response.text(),
        };

    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        error_code: "DIAGNOSE_BACKEND_UNAVAILABLE",
        message: "Backend diagnose service is unavailable.",
      },
      { status: 502 }
    );
  }
}
