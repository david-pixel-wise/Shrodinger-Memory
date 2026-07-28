# -------------------------------------------------
# 1. Settings
n      <- 10           # flips per experiment
p      <- 0.5          # probability of a head
reps   <- 500          # how many repetitions (larger → smoother histogram)

# -------------------------------------------------
# 2. Simulate the experiment
set.seed(2026)                              # optional, for reproducibility
heads <- rbinom(reps, size = n, prob = p)   # number of heads in each run
par(mar = c(5, 4, 12, 1) + 0.0)

# -------------------------------------------------
# 3. Plot the empirical distribution (histogram)
hist(heads,
     breaks = seq(-0.5, n + 0.5, by = 1),   # one bar per possible count
     freq   = FALSE,                        # density on the y‑axis
     ylim = c(0, 0.25),                     # increase the y limit
     col    = "steelblue",
     main   = paste("Distribution of heads in", reps,
                    "\nexperiments of 100 coin flips"),
     line   = 1,
     xlab   = "Heads",
     ylab   = "Density")

# -------------------------------------------------
# 4. Add the normal approximation
mu    <- n * p                     # mean  = 50
sigma <- sqrt(n * p * (1 - p))     # sd    = 5

curve(dnorm(x, mean = mu, sd = sigma),
      from = mu - 4 * sigma,
      to   = mu + 4 * sigma,
      col  = "red",
      lwd  = 2,
      add  = TRUE)
