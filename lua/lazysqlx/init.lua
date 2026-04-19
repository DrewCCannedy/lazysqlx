-- lazysqlx.nvim: floating-terminal launcher for the lazysqlx TUI.
--
-- Mirrors lazygit.nvim's ergonomics: :LazySqlx opens the TUI in a centered
-- float; pressing `e` inside the TUI closes the float and drops the user on
-- the edited migration file in a new tab (via remote-send -> on_edit()).

local M = {}

M.config = {
  cmd = "lazysqlx",
  args = {},
  width = 0.85,
  height = 0.85,
  border = "rounded",
  title = " lazysqlx ",
  title_pos = "center",
}

M.state = { buf = nil, win = nil, job = nil }

function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", M.config, opts or {})
end

local function float_dims()
  local width = math.floor(vim.o.columns * M.config.width)
  local height = math.floor(vim.o.lines * M.config.height)
  return {
    width = width,
    height = height,
    row = math.floor((vim.o.lines - height) / 2),
    col = math.floor((vim.o.columns - width) / 2),
  }
end

local function is_open()
  return M.state.win ~= nil and vim.api.nvim_win_is_valid(M.state.win)
end

function M.close()
  if is_open() then
    vim.api.nvim_win_close(M.state.win, true)
  end
  if M.state.buf and vim.api.nvim_buf_is_valid(M.state.buf) then
    vim.api.nvim_buf_delete(M.state.buf, { force = true })
  end
  M.state = { buf = nil, win = nil, job = nil }
end

function M.open(opts)
  opts = opts or {}
  if is_open() then
    vim.api.nvim_set_current_win(M.state.win)
    return
  end

  if vim.fn.executable(M.config.cmd) ~= 1 then
    vim.notify(("lazysqlx: %q not on PATH"):format(M.config.cmd), vim.log.levels.ERROR)
    return
  end

  local buf = vim.api.nvim_create_buf(false, true)
  local dims = float_dims()
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor",
    width = dims.width,
    height = dims.height,
    row = dims.row,
    col = dims.col,
    style = "minimal",
    border = M.config.border,
    title = M.config.title,
    title_pos = M.config.title_pos,
  })

  M.state.buf = buf
  M.state.win = win

  local cmd = { M.config.cmd }
  vim.list_extend(cmd, M.config.args or {})
  vim.list_extend(cmd, opts.args or {})

  local job_opts = {
    env = {
      LAZYSQLX_NVIM_FLOAT = "1",
    },
    on_exit = vim.schedule_wrap(function()
      M.close()
    end),
  }

  if vim.fn.has("nvim-0.10") == 1 then
    job_opts.term = true
    M.state.job = vim.fn.jobstart(cmd, job_opts)
  else
    M.state.job = vim.fn.termopen(cmd, job_opts)
  end
  vim.cmd("startinsert")
end

function M.toggle(opts)
  if is_open() then
    M.close()
  else
    M.open(opts)
  end
end

-- Called via `nvim --server $NVIM --remote-send` from the Python editor
-- shim when the user presses `e` inside a floating lazysqlx. Closes the
-- float (killing the TUI process) and opens the file in a new tab.
function M.on_edit(filepath)
  M.close()
  vim.cmd("tabedit " .. vim.fn.fnameescape(filepath))
end

return M
