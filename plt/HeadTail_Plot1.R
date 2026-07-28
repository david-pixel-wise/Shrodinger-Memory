# -------------------------------------------------
# 1. Parameters
n <- 100                       # number of coin flips

# -------------------------------------------------
# 2. Simulate the 100 flips (1 = heads, 0 = tails)
set.seed(123)                  # optional, for reproducibility
flips <- rbinom(n, size = 1, prob = 0.5)

# -------------------------------------------------
# 3. Count heads and tails
heads  <- sum(flips == 1)
tails  <- sum(flips == 0)
counts <- c(Heads = heads, Tails = tails)

# -------------------------------------------------
# 4. Simple bar plot
barplot(counts,
        col        = c("steelblue", "red"),
        main       = "Result of 100 coin flips",
        line       = 0,
        ylab       = "Frequency",
        ylim       = c(0, max(counts) + 10))

# optional: add the exact numbers on top of each bar
text(x = seq_along(counts),
     y = counts,
     label = counts,
     pos = 3)
