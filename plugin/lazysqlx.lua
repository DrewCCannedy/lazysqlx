if vim.g.loaded_lazysqlx == 1 then
  return
end
vim.g.loaded_lazysqlx = 1

vim.api.nvim_create_user_command("LazySqlx", function(opts)
  require("lazysqlx").open({ args = opts.fargs })
end, { nargs = "*", desc = "Open lazysqlx in a floating terminal" })

vim.api.nvim_create_user_command("LazySqlxToggle", function(opts)
  require("lazysqlx").toggle({ args = opts.fargs })
end, { nargs = "*", desc = "Toggle the lazysqlx floating terminal" })
