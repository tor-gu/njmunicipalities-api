#!/usr/bin/env Rscript
# Export the njmunicipalities tables to CSV for loading into DynamoDB.
#
# Usage: Rscript scripts/export_data.R <git-ref> [out-dir]
#
# Installs tor-gu/njmunicipalities at <git-ref> (e.g. v1.3.0) into a temporary
# library, and writes counties.csv, municipalities.csv and SOURCE 
# to out-dir (default: data).

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1 || length(args) > 2) {
  stop("Usage: Rscript scripts/export_data.R <git-ref> [out-dir]")
}
ref <- args[[1]]
out_dir <- if (length(args) == 2) args[[2]] else "data"

lib <- file.path(tempdir(), "njmunicipalities-lib")
dir.create(lib, showWarnings = FALSE)
remotes::install_github(
  "tor-gu/njmunicipalities",
  ref = ref, lib = lib, upgrade = "never", dependencies = FALSE, quiet = TRUE
)
desc <- packageDescription("njmunicipalities", lib.loc = lib)

# municipalities is internal (R/sysdata.rda); counties is exported lazy data
ns <- loadNamespace("njmunicipalities", lib.loc = lib)
municipalities <- get("municipalities", envir = ns)
data_env <- new.env()
data(list = "counties", package = "njmunicipalities", lib.loc = lib, envir = data_env)
counties <- data_env$counties

write_table <- function(df, name) {
  df <- as.data.frame(df)
  # Written unquoted to match the format DynamoDB's CSV import was given, so
  # refuse anything that would need quoting
  needs_quoting <- vapply(df, function(col) any(grepl("[,\"\r\n]", col)), logical(1))
  if (any(needs_quoting)) {
    stop(name, ": column(s) need CSV quoting: ", paste(names(df)[needs_quoting], collapse = ", "))
  }
  if (anyNA(df)) {
    stop(name, ": contains NA values")
  }
  df <- cbind(row_number = seq_len(nrow(df)), df)
  path <- file.path(out_dir, paste0(name, ".csv"))
  write.csv(df, path, row.names = FALSE, quote = FALSE, eol = "\n")
  message("Wrote ", nrow(df), " rows to ", path)
}

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write_table(counties, "counties")
write_table(municipalities, "municipalities")

source_lines <- c(
  "package=njmunicipalities",
  paste0("version=", desc$Version),
  paste0("ref=", ref),
  paste0("commit=", desc$RemoteSha),
  paste0("exported=", format(Sys.Date()))
)
writeLines(source_lines, file.path(out_dir, "SOURCE"))
message("Wrote ", file.path(out_dir, "SOURCE"))
