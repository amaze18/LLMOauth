# Generate an Anthropic OAuth Token for Claude Pro/Max

To generate an OAuth token (`sk-ant-oat01-...`) tied to your personal Claude Pro or Max subscription, you need to use Anthropic's official Claude Code command-line tool.

This token is specifically designed for local scripts, CI pipelines, and personal automation running on your own machine.

## Step-by-Step Instructions

### 1. Install the Claude Code CLI

If you haven't already, install the official Claude Code CLI on your local machine.

You need Node.js installed first.

```bash
npm install -g @anthropic-ai/claude-code
```

### 2. Run the Setup Command

Initiate the OAuth authentication flow by running:

```bash
claude setup-token
```

### 3. Complete Browser Sign-In

The CLI will either:

* Open a browser window automatically, or
* Provide a URL for you to open manually

Sign in using the Anthropic account that has your active Claude Pro or Max subscription.

### 4. Paste the Authorization Code

After signing in, the browser will:

* Display an authorization code, or
* Redirect you to a URL containing the authorization information

If prompted by the CLI, copy the code (or full redirect URL, depending on the prompt) and paste it back into your terminal.

### 5. Copy Your OAuth Token

After successful authentication, the CLI will output a token similar to:

```text
sk-ant-oat01-XXXXXXXXXXXXXXXXXXXXXXXXXX
```

Copy the entire token string.

## Using the Token Securely

Store the token in a local environment variable rather than embedding it directly in code.

```bash
# In your local .env file
ANTHROPIC_API_KEY=sk-ant-oat01-your-token-here
```

## Security Reminder

This token provides direct access to your personal Anthropic account.

Treat it like a password:

* Do not hardcode it into shared scripts.
* Do not share it with teammates.
* Do not commit it to Git repositories.
* Do not expose it in public CI/CD logs.
* Store it securely using environment variables or a secrets manager.

**Final reminder:** This token is a direct pipeline to your personal account. Treat it like a password. Never commit it to a GitHub repository or share it publicly.
