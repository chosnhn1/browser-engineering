# Exercise Project for "Browser Engineering"

This repo is a personal step-by-step exercise of "Web Browser Engineering" by Panchekha & Harrelson.

[Website](https://browser.engineering/)

## Table of Contents

* Introduction
  1. Preface
  2. Browsers and the Web
  3. History of the Web
* Part 1: Loading Pages
  1. Downloading Web Pages
  2. Drawing to the Screen
  3. Formatting Text
* Part 2: Viewing Documents
  4. Constructing an HTML Tree
  5. Laying Out Pages
  6. Applying Author Styles
  7. Handling Buttons and Links
* Part 3: Running Applications
  8. Sending Information to Servers
  9. Running Interactive Scripts
  10. Keeping Data Private
* Part 4: Modern Browsers
  11. Adding Visual Effects
  12. Scheduling Tasks and Threads
  13. Animating and Compositing
  14. Making Content Accessible
  15. Supporting Embedded Content
  16. Reusing Previous Computation
* Conclusion
  1. What Wasn't Covered
  2. A Changing Landscape

## Exercises

* Part 1
  * Chapter 1
    1. HTTP/1.1 (✅)
    2. File URLs
    3. `data`
    4. Entities
    5. `view-source`
    6. Keep-alive
    7. Redirects
    8. Caching
    9. Compression (✅)
  * Chapter 2
    1. Line breaks
    2. Mouse wheel
    3. Resizing
    4. Scrollbar
    5. Emoji
    6. `about:blank`
    7. Alternate text direction
  * Chapter 3
    1. Centered text
    2. Superscripts
    3. Soft hyphens
    4. Small caps
    5. Preformatted text
  * Chapter 4
    1. Comments
    2. Paragraphs
    3. Scripts
    4. Quoted attributes
    5. Syntax highlighting
    6. Mis-nested formatting tags
  * Chapter 5
    1. Links bar
    2. Hidden head (✅)
    3. Bullets (✅)
    4. Table of contents
    5. Anonymous block boxes
    6. Run-ins
  * Chapter 6
    1. Fonts
    2. Width/height
    3. Class selectors
    4. display
    5. Shorthand properties
    6. Inline style sheets
    7. Fast descendant selectors
    8. Selector sequences
    9. `!important`
    10. `:has` selectors

## Notes

### Chapter 6: Applying Author Styles

building recursive parsing functions: `CSSParser`

### Chapter 7

#### The process of using "address bar"

1. move focus to address bar via click
2. the click do select all (for convenience)
3. type => address bar
4. bar updates as user types; not navigates yet
5. type "Enter" to actually navigates to that page
