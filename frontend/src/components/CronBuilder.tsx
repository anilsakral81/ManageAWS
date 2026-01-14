import { useState, useEffect } from 'react'
import {
  Box,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Typography,
  Chip,
  ToggleButtonGroup,
  ToggleButton,
  Paper,
  Alert,
} from '@mui/material'
import { AccessTime, Info } from '@mui/icons-material'

interface CronBuilderProps {
  value: string
  onChange: (cronExpression: string) => void
  error?: string
}

interface CronPreset {
  label: string
  cron: string
  description: string
}

const PRESETS: CronPreset[] = [
  { label: 'Every day at 6 PM', cron: '0 18 * * *', description: 'Daily at 6:00 PM' },
  { label: 'Every day at 8 AM', cron: '0 8 * * *', description: 'Daily at 8:00 AM' },
  { label: 'Every day at 10 PM', cron: '0 22 * * *', description: 'Daily at 10:00 PM' },
  { label: 'Weekdays at 6 PM', cron: '0 18 * * 1-5', description: 'Monday-Friday at 6:00 PM' },
  { label: 'Weekdays at 8 AM', cron: '0 8 * * 1-5', description: 'Monday-Friday at 8:00 AM' },
  { label: 'Weekend at 10 AM', cron: '0 10 * * 0,6', description: 'Saturday-Sunday at 10:00 AM' },
  { label: 'Every 6 hours', cron: '0 */6 * * *', description: 'Every 6 hours' },
  { label: 'Every 12 hours', cron: '0 */12 * * *', description: 'Every 12 hours' },
]

const DAYS_OF_WEEK = [
  { value: '1', label: 'Mon' },
  { value: '2', label: 'Tue' },
  { value: '3', label: 'Wed' },
  { value: '4', label: 'Thu' },
  { value: '5', label: 'Fri' },
  { value: '6', label: 'Sat' },
  { value: '0', label: 'Sun' },
]

export default function CronBuilder({ value, onChange, error }: CronBuilderProps) {
  const [mode, setMode] = useState<'preset' | 'simple' | 'advanced'>('preset')
  const [selectedPreset, setSelectedPreset] = useState('')
  
  // Simple mode state
  const [hour, setHour] = useState('18')
  const [minute, setMinute] = useState('0')
  const [selectedDays, setSelectedDays] = useState<string[]>(['1', '2', '3', '4', '5'])
  
  // Advanced mode
  const [customCron, setCustomCron] = useState(value || '0 18 * * 1-5')

  useEffect(() => {
    // Initialize based on current value
    if (value) {
      const preset = PRESETS.find(p => p.cron === value)
      if (preset) {
        setMode('preset')
        setSelectedPreset(value)
      } else {
        setCustomCron(value)
      }
    }
  }, [])

  const handlePresetChange = (presetCron: string) => {
    setSelectedPreset(presetCron)
    onChange(presetCron)
  }

  const handleSimpleModeUpdate = () => {
    // Build cron from simple inputs
    const daysPart = selectedDays.length === 7 
      ? '*' 
      : selectedDays.sort().join(',')
    
    const cron = `${minute} ${hour} * * ${daysPart}`
    onChange(cron)
  }

  useEffect(() => {
    if (mode === 'simple') {
      handleSimpleModeUpdate()
    }
  }, [hour, minute, selectedDays, mode])

  const handleDaysChange = (_event: React.MouseEvent<HTMLElement>, newDays: string[]) => {
    if (newDays.length > 0) {
      setSelectedDays(newDays)
    }
  }

  const getCronDescription = (cron: string): string => {
    const parts = cron.split(' ')
    if (parts.length !== 5) return 'Invalid cron expression'
    
    const [min, hr, , , day] = parts
    
    let timeStr = `at ${hr.padStart(2, '0')}:${min.padStart(2, '0')}`
    
    if (hr.includes('*/')) {
      const interval = hr.split('*/')[1]
      timeStr = `every ${interval} hours`
    }
    
    let dayStr = 'every day'
    if (day === '1-5') dayStr = 'on weekdays (Mon-Fri)'
    else if (day === '0,6') dayStr = 'on weekends (Sat-Sun)'
    else if (day !== '*') dayStr = `on selected days`
    
    return `Runs ${timeStr} ${dayStr}`
  }

  return (
    <Box>
      <Stack spacing={2}>
        {/* Mode Selector */}
        <FormControl size="small">
          <InputLabel>Schedule Type</InputLabel>
          <Select
            value={mode}
            label="Schedule Type"
            onChange={(e) => setMode(e.target.value as any)}
          >
            <MenuItem value="preset">Quick Presets</MenuItem>
            <MenuItem value="simple">Simple Builder</MenuItem>
            <MenuItem value="advanced">Advanced (Cron)</MenuItem>
          </Select>
        </FormControl>

        {/* Preset Mode */}
        {mode === 'preset' && (
          <FormControl fullWidth>
            <InputLabel>Select Schedule</InputLabel>
            <Select
              value={selectedPreset}
              label="Select Schedule"
              onChange={(e) => handlePresetChange(e.target.value)}
            >
              {PRESETS.map((preset) => (
                <MenuItem key={preset.cron} value={preset.cron}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <AccessTime fontSize="small" />
                    <Box>
                      <Typography variant="body2">{preset.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {preset.description}
                      </Typography>
                    </Box>
                  </Stack>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        {/* Simple Builder Mode */}
        {mode === 'simple' && (
          <Stack spacing={2}>
            <Stack direction="row" spacing={2}>
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Hour</InputLabel>
                <Select
                  value={hour}
                  label="Hour"
                  onChange={(e) => setHour(e.target.value)}
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <MenuItem key={i} value={i.toString()}>
                      {i.toString().padStart(2, '0')}:00
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Minute</InputLabel>
                <Select
                  value={minute}
                  label="Minute"
                  onChange={(e) => setMinute(e.target.value)}
                >
                  {[0, 15, 30, 45].map((min) => (
                    <MenuItem key={min} value={min.toString()}>
                      :{min.toString().padStart(2, '0')}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>

            <Box>
              <Typography variant="body2" gutterBottom>
                Select Days
              </Typography>
              <ToggleButtonGroup
                value={selectedDays}
                onChange={handleDaysChange}
                aria-label="days of week"
                size="small"
              >
                {DAYS_OF_WEEK.map((day) => (
                  <ToggleButton key={day.value} value={day.value} aria-label={day.label}>
                    {day.label}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            </Box>
          </Stack>
        )}

        {/* Advanced Mode */}
        {mode === 'advanced' && (
          <TextField
            fullWidth
            label="Cron Expression"
            value={customCron}
            onChange={(e) => {
              setCustomCron(e.target.value)
              onChange(e.target.value)
            }}
            error={!!error}
            helperText={error || 'Format: minute hour day month dayOfWeek (e.g., 0 18 * * 1-5)'}
            placeholder="0 18 * * 1-5"
            size="small"
          />
        )}

        {/* Current Cron Display */}
        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
          <Stack direction="row" spacing={1} alignItems="center" mb={1}>
            <Info fontSize="small" color="primary" />
            <Typography variant="subtitle2" color="primary">
              Schedule Preview
            </Typography>
          </Stack>
          <Typography variant="body2" fontFamily="monospace" gutterBottom>
            {value || '0 18 * * 1-5'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {getCronDescription(value || '0 18 * * 1-5')}
          </Typography>
        </Paper>

        {/* Help Alert */}
        <Alert severity="info" icon={<AccessTime />}>
          <Typography variant="caption">
            <strong>Common Examples:</strong>
          </Typography>
          <Typography variant="caption" component="div">
            • <Chip label="0 18 * * *" size="small" /> = Every day at 6 PM<br />
            • <Chip label="0 8 * * 1-5" size="small" /> = Weekdays at 8 AM<br />
            • <Chip label="0 */6 * * *" size="small" /> = Every 6 hours
          </Typography>
        </Alert>
      </Stack>
    </Box>
  )
}
