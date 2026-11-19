# Connect HiringCafe to your AI tool

Career informed search finds jobs through **HiringCafe**, a free job search engine that collects postings from employers' own career sites. HiringCafe publishes a connector (an MCP server) that AI tools can use:

**Name:** HiringCafe · **URL:** `https://hiringcafe.com/api/mcp`

You need no HiringCafe account and no sign-in; the connector reads public job data only. It gives your AI tool two tools, `search_jobs` and `get_job_details`. Connect it once, in the AI tool you use with this folder. The rest of the tool (fit checks, résumés, letters, the tracker) works without it.

## Claude Code

This folder already lists HiringCafe in `.mcp.json`. When you start Claude Code here, it asks whether to use the project's servers: approve **hiringcafe**. To add it yourself instead, or for every folder:

```sh
claude mcp add --transport http --scope user hiringcafe https://hiringcafe.com/api/mcp
```

Check with `/mcp` inside Claude Code: **hiringcafe** should show as connected.

## Claude apps (claude.ai, desktop and mobile)

Open **Settings → Connectors**. If **HiringCafe Job Search** is in the directory, add it. Otherwise choose **Add custom connector** and enter the name **HiringCafe** and the URL above. A connector you add on one Claude app is available in the others with the same account.

## Codex (ChatGPT's coding agent)

```sh
codex mcp add hiringcafe --url https://hiringcafe.com/api/mcp
```

Or add it to `~/.codex/config.toml` by hand:

```toml
[mcp_servers.hiringcafe]
url = "https://hiringcafe.com/api/mcp"
```

In the ChatGPT app, HiringCafe also offers **HiringCafe Job Search for ChatGPT** among the apps; use it when you work with this folder through ChatGPT.

## Gemini CLI

This folder already lists HiringCafe in `.gemini/settings.json`; Gemini CLI loads it when you trust the folder. To add it for every folder:

```sh
gemini mcp add -s user --transport http hiringcafe https://hiringcafe.com/api/mcp
```

Check with `/mcp` inside Gemini CLI.

## Any other AI tool

Add a remote MCP server (Streamable HTTP transport) named **hiringcafe** with the URL above, with no authentication. The tool's own help names the setting; it is usually under MCP servers, connectors or integrations.

## Check that it works

Ask your AI tool: "List your HiringCafe tools." It should name `search_jobs` and `get_job_details`. Then say **set up my search** (first time) or **find me 10 jobs**.

## Good to know

- **What HiringCafe sees:** the searches your agent sends (job titles, a location, filters) and the job IDs it opens. Your career record, preferences and résumés never go to HiringCafe. HiringCafe's [privacy policy](https://hiringcafe.com/private-policy) covers the connector.
- **Cloud sessions** (Claude Code on the web, Codex cloud) use the connectors set up for that service; add HiringCafe there the same way.
- **Results differ between connections.** Different versions of the connector can return different formats. The search tools keep every response as received and say when one cannot be read; nothing is invented to fill a gap.
- **Other job sources** may follow. The search is built so a new source needs only a new reader for its responses.
