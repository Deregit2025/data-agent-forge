# Resource Acquisition

As a member of the **Signal Corps**, one of our Day 1 tasks was to secure a code execution sandbox for our team using the **Cloudflare Workers free tier**. This sandbox allows the agent to execute Python or TypeScript data transformation code outside of the LLM context.

Here is the step-by-step process we went through to apply for and configure this resource for our team:

## 1. Created and Accessed the Account

- **We visited the Cloudflare Workers site:** [workers.cloudflare.com](https://workers.cloudflare.com) to sign up for a free account.
- We have created a shared account `Gemini-trp@proton.me` for our team to use.

## 2. Installed and Authenticated the Tooling

- **Installed Wrangler CLI:** Run the command: `npm install -g wrangler` in our terminal.
- **Log in:** Authenticateed our local environment with our new account by running: `wrangler login`.

## 3. Deployed the Sandbox Worker

- **Navigated to the Worker Directory:**  `cd workers`.
- **Deployed:** Run the deployment command: `wrangler deploy`.
- Once deployed, Cloudflare gave us a URL: `https://sandbox.Gemini-trp.workers.dev`.

## 4. Configure Team Access

- **Updated the Environment File:** We have added the new URL to our team’s `.env` file so the agent can use it: `SANDBOX_URL=https://sandbox.Gemini-trp.workers.dev`.

## 5. Report to the Team

- **Mob Session Briefing:** We have reported the outcome of our application and provide the access instructions to our group during the **Day 2 mob session**.
- **Resource Acquisition Report:** We have documented the status of this application, the outcomes, and the usage instructions in our team's **Resource Acquisition Report**.
