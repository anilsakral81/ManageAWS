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

// Helper function to convert local time to UTC cron
const getUTCCron = (localHour: number, localMinute: number, days: string): string => {
  const now = new Date()
  const localDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), localHour, localMinute)
  const utcHour = localDate.getUTCHours()
  const utcMinute = localDate.getUTCMinutes()
  return `${utcMinute} ${utcHour} * * ${days}`
}

// Helper to get local time display
const getLocalTimeDisplay = (hour: number): string => {
  const hour12 = hour % 12 || 12
  const amPm = hour >= 12 ? 'PM' : 'AM'
  return `${hour12}:00 ${amPm}`
}

// Generate presets with local time
const getPresets = (): CronPreset[] => [
  { label: `Every day at ${getLocalTimeDisplay(18)}`, cron: getUTCCron(18, 0, '*'), description: `Daily at ${getLocalTimeDisplay(18)}` },
  { label: `Every day at ${getLocalTimeDisplay(8)}`, cron: getUTCCron(8, 0, '*'), description: `Daily at ${getLocalTimeDisplay(8)}` },
  { label: `Every day at ${getLocalTimeDisplay(22)}`, cron: getUTCCron(22, 0, '*'), description: `Daily at ${getLocalTimeDisplay(22)}` },
  { label: `Weekdays at ${getLocalTimeDisplay(18)}`, cron: getUTCCron(18, 0, '1-5'), description: `Monday-Friday at ${getLocalTimeDisplay(18)}` },
  { label: `Weekdays at ${getLocalTimeDisplay(8)}`, cron: getUTCCron(8, 0, '1-5'), description: `Monday-Friday at ${getLocalTimeDisplay(8)}` },
  { label: `Weekend at ${getLocalTimeDisplay(10)}`, cron: getUTCCron(10, 0, '0,6'), description: `Saturday-Sunday at ${getLocalTimeDisplay(10)}` },
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
  const PRESETS = getPresets()
  
  // Simple mode state (in local time)
  const [hour, setHour] = useState('18')
  const [minute, setMinute] = useState('0')
  const [selectedDays, setSelectedDays] = useState<string[]>(['1', '2', '3', '4', '5'])
  
  // Advanced mode
  const [customCron, setCustomCron] = useState(value || '0 18 * * 1-5')

  useEffect(() => {
    // Initialize based on current value
    if (value) {
      const presets = getPresets()
      const preset = presets.find(p => p.cron === value)
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
    // Convert local time to UTC
    const now = new Date()
    const localDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), parseInt(hour), parseInt(minute))
    const utcHour = localDate.getUTCHours()
    const utcMinute = localDate.getUTCMinutes()
    
    // Build cron from simple inputs in UTC
    const daysPart = selectedDays.length === 7 
      ? '*' 
      : selectedDays.sort().join(',')
    
    const cron = `${utcMinute} ${utcHour} * * ${daysPart}`
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
    
    let timeStr = ''
    
    if (hr.includes('*/')) {
      const interval = hr.split('*/')[1]
      timeStr = `every ${interval} hours`
    } else {
      // Convert UTC time to local time
      const utcHour = parseInt(hr)
      const utcMinute = parseInt(min)
      
      const now = new Date()
      const utcDate = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), utcHour, utcMinute))
      
      const localHour = utcDate.getHours()
      const localMinute = utcDate.getMinutes()
      const localHour12 = localHour % 12 || 12
      const localAmPm = localHour >= 12 ? 'PM' : 'AM'
      
      const utcHour12 = utcHour % 12 || 12
      const utcAmPm = utcHour >= 12 ? 'PM' : 'AM'
      
      const tzAbbr = new Date().toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop()
      
      timeStr = `at ${localHour12}:${localMinute.toString().padStart(2, '0')} ${localAmPm} ${tzAbbr} (${utcHour12}:${utcMinute.toString().padStart(2, '0')} ${utcAmPm} UTC)`
    }
    
    // Get day description with day names
    let dayStr = 'every day'
    if (day === '1-5') {
      dayStr = 'on weekdays (Mon-Fri)'
    } else if (day === '0,6') {
      dayStr = 'on weekends (Sat-Sun)'
    } else if (day === '1,2,3,4,5') {
      dayStr = 'on weekdays (Mon-Fri)'
    } else if (day !== '*') {
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
      const selectedDays = day.split(',').map(d => dayNames[parseInt(d)]).filter(Boolean)
      if (selectedDays.length > 0) {
        dayStr = `on ${selectedDays.join(', ')}`
      } else {
        dayStr = 'on selected days'
      }
    }
    
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
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Hour</InputLabel>
                <Select
                  value={hour}
                  label="Hour"
                  onChange={(e) => setHour(e.target.value)}
                >
                  {Array.from({ length: 24 }, (_, i) => {
                    const hour12 = i % 12 || 12
                    const amPm = i >= 12 ? 'PM' : 'AM'
                    return (
                      <MenuItem key={i} value={i.toString()}>
                        {hour12}:00 {amPm}
                      </MenuItem>
                    )
                  })}
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
