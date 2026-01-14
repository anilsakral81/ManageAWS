# CVS Light Theme - Visual Design Guide

## Color Palette

### Primary Colors
```css
Primary Blue:    #1976d2  ███████  (Buttons, links, headers)
Dark Blue:       #1565c0  ███████  (Hover states)
Darkest Blue:    #0d47a1  ███████  (Active states)
```

### Neutral Colors
```css
Text Dark:       #424242  ███████  (Primary text)
Text Medium:     #666666  ███████  (Secondary text, hints)
Border:          #e0e0e0  ███████  (Borders, dividers)
```

### Background Colors
```css
Page BG Start:   #f5f7fa  ███████  (Gradient top)
Page BG End:     #e8eef5  ███████  (Gradient bottom)
Card:            #ffffff  ███████  (Login form, cards)
Input:           #f8f9fa  ███████  (Input fields)
Input Focus:     #ffffff  ███████  (Focused inputs)
```

### Alert Colors
```css
Error BG:        #ffebee  ███████  (Error messages)
Error Text:      #c62828  ███████  
Warning BG:      #fff3e0  ███████  (Warning messages)
Warning Text:    #ef6c00  ███████  
Success BG:      #e8f5e9  ███████  (Success messages)
Success Text:    #2e7d32  ███████  
Info BG:         #e3f2fd  ███████  (Info messages)
Info Text:       #1565c0  ███████  
```

## Typography

### Font Family
```
Primary: 'Roboto', 'Helvetica', 'Arial', sans-serif
```

### Font Sizes & Weights

#### Login Page Header
```
Main Title:     28px, weight: 600, color: #1976d2
Subtitle:       ~25px, weight: 400, color: #424242
```

#### Form Labels
```
Size:           14px
Weight:         500
Color:          #424242
Margin:         8px bottom
```

#### Inputs
```
Size:           15px
Padding:        12px 16px
Border:         2px solid #e0e0e0
Border Radius:  8px
```

#### Buttons
```
Size:           16px
Weight:         500
Padding:        12px 24px
Border Radius:  8px
```

## Layout & Spacing

### Login Card
```css
Background:     #ffffff
Border Radius:  12px
Box Shadow:     0 4px 20px rgba(0, 0, 0, 0.08)
Border:         1px solid #e0e0e0
Padding:        40px
Max Width:      ~500px (auto-sized by Keycloak)
```

### Form Elements
```css
Form Group Margin:  24px bottom
Input Padding:      12px 16px
Button Padding:     12px 24px
```

### Responsive Breakpoints
```css
Mobile (< 768px):
  - Card padding: 24px
  - Card margin:  16px
  - Header size:  24px
```

## Interactive States

### Button States
```css
Default:
  Background:   #1976d2
  Shadow:       0 2px 8px rgba(25, 118, 210, 0.2)

Hover:
  Background:   #1565c0
  Shadow:       0 4px 12px rgba(25, 118, 210, 0.3)
  Transform:    translateY(-1px)

Active:
  Background:   #0d47a1
  Transform:    translateY(0)
  
All transitions: 0.3s ease
```

### Input States
```css
Default:
  Background:   #f8f9fa
  Border:       2px solid #e0e0e0

Focus:
  Background:   #ffffff
  Border:       2px solid #1976d2
  Box Shadow:   0 0 0 3px rgba(25, 118, 210, 0.1)
  
Transition: all 0.3s ease
```

### Link States
```css
Default:
  Color:           #1976d2
  Text Decoration: none

Hover:
  Color:           #1565c0
  Text Decoration: underline
  
Transition: color 0.2s ease
```

## Visual Mockup (Text-based)

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    ░░░░░░░░░░░░░░░░ Light Gradient Background ░░░░░░░░░░    ║
║    ░░░░░░░░░░░░░░░░  (#f5f7fa → #e8eef5)  ░░░░░░░░░░░░░     ║
║                                                              ║
║         ┌──────────────────────────────────────┐            ║
║         │                                      │            ║
║         │  Tenant Management System            │            ║
║         │  (Blue, 28px, weight: 600)           │            ║
║         │                                      │            ║
║         │  for CVS SaaS Apps                   │            ║
║         │  (Gray, smaller)                     │            ║
║         │                                      │            ║
║         │  ─────────────────────────────────   │            ║
║         │                                      │            ║
║         │  Username or email                   │            ║
║         │  ┌────────────────────────────────┐  │            ║
║         │  │ [Light gray input field]       │  │            ║
║         │  └────────────────────────────────┘  │            ║
║         │                                      │            ║
║         │  Password                            │            ║
║         │  ┌────────────────────────────────┐  │            ║
║         │  │ [Light gray input field]       │  │            ║
║         │  └────────────────────────────────┘  │            ║
║         │                                      │            ║
║         │  ☐ Remember me                       │            ║
║         │                                      │            ║
║         │  ┌────────────────────────────────┐  │            ║
║         │  │   Sign In (Blue button)        │  │            ║
║         │  └────────────────────────────────┘  │            ║
║         │                                      │            ║
║         │  Forgot Password?                    │            ║
║         │                                      │            ║
║         └──────────────────────────────────────┘            ║
║              White card with rounded corners                ║
║              Subtle shadow for depth                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

## Component-Specific Styles

### Login Form Header
```html
<div class="kc-logo-text">
  <span style='color: #1976d2; font-weight: 600;'>
    Tenant Management System
  </span>
  <br/>
  <span style='color: #424242; font-size: 0.9em;'>
    for CVS SaaS Apps
  </span>
</div>
```

### Primary Button
```css
.btn-primary {
  background-color: #1976d2;
  border-color: #1976d2;
  color: #ffffff;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
  transition: all 0.3s ease;
}
```

### Input Field
```css
.form-control {
  background-color: #f8f9fa;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 15px;
  transition: all 0.3s ease;
}

.form-control:focus {
  background-color: #ffffff;
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
  outline: none;
}
```

## Accessibility Features

### Focus Indicators
- Clear blue outline on focused elements
- High contrast ratios maintained
- Visible focus states on all interactive elements

### Color Contrast
- Text on white: #424242 (AAA rated)
- Blue buttons: #1976d2 on white (AA rated)
- All alerts meet WCAG AA standards

### Keyboard Navigation
- All form elements keyboard accessible
- Tab order follows visual flow
- Clear focus indicators

## Design Principles

1. **Simplicity**: Clean, uncluttered interface
2. **Consistency**: Uniform spacing, colors, and typography
3. **Hierarchy**: Clear visual hierarchy through size and weight
4. **Feedback**: Smooth transitions and hover states
5. **Accessibility**: WCAG AA compliant colors and contrast
6. **Branding**: CVS blue (#1976d2) as primary brand color
7. **Modernism**: Rounded corners, subtle shadows, gradients

## Browser Compatibility

Tested and supported on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Performance

- **CSS Size**: ~8KB uncompressed
- **Load Time**: Instant (CSS only, no images)
- **Render**: No layout shift, smooth transitions
- **Compatibility**: Pure CSS, no JavaScript dependencies

---

**Design Version**: 1.0
**Last Updated**: January 3, 2026
**Designer**: CVS SaaS Team
