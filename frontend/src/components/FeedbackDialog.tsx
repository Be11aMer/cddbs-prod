import {
  Box,
  Typography,
  Paper,
  Stack,
  Divider,
  Alert,
  IconButton,
  Dialog,
  AppBar,
  Toolbar,
  Slide,
  Container,
  TextField,
  Rating,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Button,
  CircularProgress,
  MenuItem,
  Select,
  InputLabel,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import SendIcon from "@mui/icons-material/Send";
import StarIcon from "@mui/icons-material/Star";
import { forwardRef, ReactElement, Ref, useState } from "react";
import { TransitionProps } from "@mui/material/transitions";
import { submitFeedback } from "../api";

const Transition = forwardRef(function Transition(
  props: TransitionProps & { children: ReactElement },
  ref: Ref<unknown>
) {
  return <Slide direction="up" ref={ref} {...props} />;
});

interface Props {
  open: boolean;
  onClose: () => void;
}

const ratingLabels: Record<number, string> = {
  1: "Very Poor",
  2: "Poor",
  3: "Acceptable",
  4: "Good",
  5: "Excellent",
};

const RequiredLabel = ({ children }: { children: string }) => (
  <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
    {children} <span style={{ color: "#ef4444" }}>*</span>
  </Typography>
);

export const FeedbackDialog = ({ open, onClose }: Props) => {
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [testerName, setTesterName] = useState("");
  const [testerRole, setTesterRole] = useState("");
  const [overallRating, setOverallRating] = useState<number | null>(null);
  const [accuracyRating, setAccuracyRating] = useState<number | null>(null);
  const [usabilityRating, setUsabilityRating] = useState<number | null>(null);
  const [bugsEncountered, setBugsEncountered] = useState("");
  const [misleadingOutputs, setMisleadingOutputs] = useState("");
  const [missingFeatures, setMissingFeatures] = useState("");
  const [uxPainPoints, setUxPainPoints] = useState("");
  const [professionalConcerns, setProfessionalConcerns] = useState("");
  const [wouldRecommend, setWouldRecommend] = useState("");
  const [additionalComments, setAdditionalComments] = useState("");

  const canSubmit =
    overallRating !== null &&
    accuracyRating !== null &&
    usabilityRating !== null &&
    bugsEncountered.trim().length >= 5;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitFeedback({
        tester_name: testerName || undefined,
        tester_role: testerRole || undefined,
        overall_rating: overallRating!,
        accuracy_rating: accuracyRating!,
        usability_rating: usabilityRating!,
        bugs_encountered: bugsEncountered,
        misleading_outputs: misleadingOutputs || undefined,
        missing_features: missingFeatures || undefined,
        ux_pain_points: uxPainPoints || undefined,
        professional_concerns: professionalConcerns || undefined,
        would_recommend: wouldRecommend || undefined,
        additional_comments: additionalComments || undefined,
      });
      setSubmitted(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to submit feedback";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (submitted) {
      // Reset form on close after successful submission
      setTesterName("");
      setTesterRole("");
      setOverallRating(null);
      setAccuracyRating(null);
      setUsabilityRating(null);
      setBugsEncountered("");
      setMisleadingOutputs("");
      setMissingFeatures("");
      setUxPainPoints("");
      setProfessionalConcerns("");
      setWouldRecommend("");
      setAdditionalComments("");
      setSubmitted(false);
      setError(null);
    }
    onClose();
  };

  return (
    <Dialog
      fullScreen
      open={open}
      onClose={handleClose}
      TransitionComponent={Transition}
      sx={{
        "& .MuiDialog-paper": {
          backgroundColor: "#020617",
          backgroundImage:
            "radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 1) 0%, rgba(2, 6, 23, 1) 100%)",
        },
      }}
    >
      <AppBar
        sx={{
          position: "relative",
          backgroundColor: "rgba(15, 23, 42, 0.8)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(148,163,184,0.1)",
        }}
      >
        <Toolbar>
          <IconButton edge="start" color="inherit" onClick={handleClose}>
            <CloseIcon />
          </IconButton>
          <Typography sx={{ ml: 2, flex: 1 }} variant="h6" fontWeight={700}>
            Leave Feedback for Developers
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 4 }}>
        {submitted ? (
          <Box sx={{ textAlign: "center", py: 8 }}>
            <Typography variant="h4" fontWeight={800} sx={{ mb: 2 }}>
              Thank you for your feedback!
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
              Your input helps us build a better intelligence analysis tool. Every bug report
              and suggestion matters.
            </Typography>
            <Button variant="contained" onClick={handleClose} sx={{ borderRadius: 2, px: 4 }}>
              Close
            </Button>
          </Box>
        ) : (
          <>
            <Alert
              severity="info"
              sx={{
                mb: 4,
                borderRadius: 3,
                backgroundColor: "rgba(59,130,246,0.05)",
                border: "1px solid rgba(59,130,246,0.2)",
              }}
            >
              <Typography variant="subtitle2" fontWeight={700}>
                Honest feedback makes better software
              </Typography>
              <Typography variant="body2">
                Please be specific and critical. Report everything — broken features, confusing UI,
                inaccurate AI outputs, missing functionality. Fields marked with{" "}
                <span style={{ color: "#ef4444", fontWeight: 700 }}>*</span> are mandatory.
              </Typography>
            </Alert>

            {error && (
              <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
                {error}
              </Alert>
            )}

            <Stack spacing={4}>
              {/* Section 1: About You (optional) */}
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: "1px solid rgba(148,163,184,0.1)",
                  backgroundColor: "rgba(148,163,184,0.03)",
                }}
              >
                <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
                  About You (optional)
                </Typography>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <TextField
                    label="Your Name"
                    value={testerName}
                    onChange={(e) => setTesterName(e.target.value)}
                    fullWidth
                    size="small"
                    placeholder="e.g. Jane Doe"
                  />
                  <FormControl fullWidth size="small">
                    <InputLabel>Your Role</InputLabel>
                    <Select
                      value={testerRole}
                      onChange={(e) => setTesterRole(e.target.value)}
                      label="Your Role"
                    >
                      <MenuItem value="analyst">Intelligence Analyst</MenuItem>
                      <MenuItem value="developer">Developer / Engineer</MenuItem>
                      <MenuItem value="researcher">Researcher</MenuItem>
                      <MenuItem value="student">Student</MenuItem>
                      <MenuItem value="other">Other</MenuItem>
                    </Select>
                  </FormControl>
                </Stack>
              </Paper>

              {/* Section 2: Ratings (required) */}
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: "1px solid rgba(148,163,184,0.1)",
                  backgroundColor: "rgba(148,163,184,0.03)",
                }}
              >
                <Typography variant="h6" fontWeight={700} sx={{ mb: 0.5 }}>
                  Rate the Application
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  1 = Very Poor, 5 = Excellent. Be honest — inflated ratings don't help us improve.
                </Typography>

                <Stack spacing={3}>
                  <Box>
                    <RequiredLabel>Overall Experience</RequiredLabel>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      How would you rate the application as a whole?
                    </Typography>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Rating
                        value={overallRating}
                        onChange={(_, v) => setOverallRating(v)}
                        icon={<StarIcon sx={{ fontSize: 32 }} />}
                        emptyIcon={<StarIcon sx={{ fontSize: 32, opacity: 0.3 }} />}
                      />
                      {overallRating && (
                        <Typography variant="body2" color="text.secondary">
                          {ratingLabels[overallRating]}
                        </Typography>
                      )}
                    </Stack>
                  </Box>

                  <Divider sx={{ opacity: 0.1 }} />

                  <Box>
                    <RequiredLabel>AI Output Accuracy</RequiredLabel>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      How accurate and reliable were the generated intelligence briefings?
                    </Typography>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Rating
                        value={accuracyRating}
                        onChange={(_, v) => setAccuracyRating(v)}
                        icon={<StarIcon sx={{ fontSize: 32 }} />}
                        emptyIcon={<StarIcon sx={{ fontSize: 32, opacity: 0.3 }} />}
                      />
                      {accuracyRating && (
                        <Typography variant="body2" color="text.secondary">
                          {ratingLabels[accuracyRating]}
                        </Typography>
                      )}
                    </Stack>
                  </Box>

                  <Divider sx={{ opacity: 0.1 }} />

                  <Box>
                    <RequiredLabel>Usability & Interface</RequiredLabel>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      How easy was it to navigate and use the application?
                    </Typography>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Rating
                        value={usabilityRating}
                        onChange={(_, v) => setUsabilityRating(v)}
                        icon={<StarIcon sx={{ fontSize: 32 }} />}
                        emptyIcon={<StarIcon sx={{ fontSize: 32, opacity: 0.3 }} />}
                      />
                      {usabilityRating && (
                        <Typography variant="body2" color="text.secondary">
                          {ratingLabels[usabilityRating]}
                        </Typography>
                      )}
                    </Stack>
                  </Box>
                </Stack>
              </Paper>

              {/* Section 3: Critical feedback (bugs required) */}
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: "1px solid rgba(148,163,184,0.1)",
                  backgroundColor: "rgba(148,163,184,0.03)",
                }}
              >
                <Typography variant="h6" fontWeight={700} sx={{ mb: 0.5 }}>
                  Critical Feedback
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  This section is the most valuable. Please describe issues in detail — what happened,
                  where, and what you expected instead.
                </Typography>

                <Stack spacing={3}>
                  <Box>
                    <RequiredLabel>Bugs & Errors Encountered</RequiredLabel>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      Describe any crashes, broken features, incorrect behavior, or error messages you saw.
                      Write "None found" if you encountered no bugs.
                    </Typography>
                    <TextField
                      value={bugsEncountered}
                      onChange={(e) => setBugsEncountered(e.target.value)}
                      multiline
                      rows={3}
                      fullWidth
                      placeholder="e.g. Clicking 'View Report' on a failed run shows a blank page instead of the error message..."
                      error={bugsEncountered.length > 0 && bugsEncountered.length < 5}
                      helperText={
                        bugsEncountered.length > 0 && bugsEncountered.length < 5
                          ? "Please write at least 5 characters"
                          : undefined
                      }
                    />
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
                      Misleading or Inaccurate AI Outputs
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      Did the AI generate false claims, hallucinated sources, biased assessments, or
                      unreasonable confidence levels?
                    </Typography>
                    <TextField
                      value={misleadingOutputs}
                      onChange={(e) => setMisleadingOutputs(e.target.value)}
                      multiline
                      rows={3}
                      fullWidth
                      placeholder="e.g. The briefing for BBC claimed it was state-controlled media, which is inaccurate..."
                    />
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
                      UX Pain Points
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      What was confusing, hard to find, or frustrating? Were there any interactions that
                      didn't behave as you expected?
                    </Typography>
                    <TextField
                      value={uxPainPoints}
                      onChange={(e) => setUxPainPoints(e.target.value)}
                      multiline
                      rows={3}
                      fullWidth
                      placeholder="e.g. I couldn't tell if the analysis was still running or had stalled — no progress indicator..."
                    />
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
                      Professional Concerns
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      As an analyst/researcher: Would this tool be acceptable in a professional setting?
                      What standards does it fall short of?
                    </Typography>
                    <TextField
                      value={professionalConcerns}
                      onChange={(e) => setProfessionalConcerns(e.target.value)}
                      multiline
                      rows={3}
                      fullWidth
                      placeholder="e.g. Reports lack source attribution. An analyst would need verifiable references for each claim..."
                    />
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
                      Missing Features or Capabilities
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                      What functionality is missing that you would expect or need?
                    </Typography>
                    <TextField
                      value={missingFeatures}
                      onChange={(e) => setMissingFeatures(e.target.value)}
                      multiline
                      rows={2}
                      fullWidth
                      placeholder="e.g. No way to compare two outlets side-by-side, no export to PDF..."
                    />
                  </Box>
                </Stack>
              </Paper>

              {/* Section 4: Overall verdict */}
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: "1px solid rgba(148,163,184,0.1)",
                  backgroundColor: "rgba(148,163,184,0.03)",
                }}
              >
                <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
                  Final Verdict
                </Typography>

                <FormControl sx={{ mb: 3 }}>
                  <FormLabel sx={{ fontWeight: 700, fontSize: "0.875rem", mb: 1 }}>
                    Would you recommend this tool to a colleague?
                  </FormLabel>
                  <RadioGroup
                    row
                    value={wouldRecommend}
                    onChange={(e) => setWouldRecommend(e.target.value)}
                  >
                    <FormControlLabel value="yes" control={<Radio />} label="Yes" />
                    <FormControlLabel value="maybe" control={<Radio />} label="Maybe" />
                    <FormControlLabel value="no" control={<Radio />} label="No" />
                  </RadioGroup>
                </FormControl>

                <Box>
                  <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
                    Additional Comments
                  </Typography>
                  <TextField
                    value={additionalComments}
                    onChange={(e) => setAdditionalComments(e.target.value)}
                    multiline
                    rows={3}
                    fullWidth
                    placeholder="Anything else you'd like the development team to know..."
                  />
                </Box>
              </Paper>

              {/* Submit */}
              <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 2 }}>
                <Button
                  variant="outlined"
                  onClick={handleClose}
                  sx={{ borderRadius: 2, px: 3 }}
                >
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  onClick={handleSubmit}
                  disabled={!canSubmit || submitting}
                  startIcon={submitting ? <CircularProgress size={18} /> : <SendIcon />}
                  sx={{ borderRadius: 2, px: 4 }}
                >
                  {submitting ? "Submitting..." : "Submit Feedback"}
                </Button>
              </Box>

              {!canSubmit && (
                <Typography variant="caption" color="text.secondary" sx={{ textAlign: "right" }}>
                  Please fill in all three ratings and the bugs field to submit.
                </Typography>
              )}
            </Stack>
          </>
        )}
      </Container>
    </Dialog>
  );
};
