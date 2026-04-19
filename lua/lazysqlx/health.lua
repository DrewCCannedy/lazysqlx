-- `:checkhealth lazysqlx` — verifies the plugin's external requirements.

local M = {}

local health = vim.health or require("health")
local start = health.start or health.report_start
local ok = health.ok or health.report_ok
local warn = health.warn or health.report_warn
local err = health.error or health.report_error
local info = health.info or health.report_info

local function bin_version(cmd, args)
  local result = vim.fn.system({ cmd, unpack(args or { "--version" }) })
  if vim.v.shell_error ~= 0 then
    return nil
  end
  return vim.trim(vim.split(result, "\n", { plain = true })[1] or "")
end

function M.check()
  start("lazysqlx")

  if vim.fn.has("nvim-0.10") == 1 then
    ok("Neovim " .. tostring(vim.version()))
  elseif vim.fn.has("nvim-0.9") == 1 then
    warn("Neovim < 0.10 — falling back to deprecated `termopen`; upgrade recommended")
  else
    err("Neovim >= 0.9 required")
  end

  local config = require("lazysqlx").config
  local bin = config.cmd

  if vim.fn.executable(bin) == 1 then
    local v = bin_version(bin)
    ok(("`%s` found%s"):format(bin, v and (": " .. v) or ""))
  else
    err(
      ("`%s` not on PATH"):format(bin),
      { "Install with `uv tool install lazysqlx`, or set `opts.cmd` to the binary path." }
    )
  end

  if vim.fn.executable("sqlx") == 1 then
    local v = bin_version("sqlx")
    ok("`sqlx` CLI found" .. (v and (": " .. v) or ""))
  else
    err("`sqlx` CLI not on PATH", { "Install with `cargo install sqlx-cli`." })
  end

  if vim.fn.executable("nvim") == 1 then
    ok("`nvim` on PATH (needed for remote-tab / remote-send editor handoff)")
  else
    warn(
      "`nvim` not on PATH — the Python side can't call back into this session; $EDITOR will be used instead"
    )
  end

  local db = vim.env.DATABASE_URL
  if db and db ~= "" then
    info("DATABASE_URL is set")
  else
    info("DATABASE_URL not set — pass `--database-url` or rely on a local `.env`")
  end
end

return M
