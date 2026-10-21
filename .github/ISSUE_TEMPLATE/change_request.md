---
name: Change Request
about: Request a change to production systems
title: '[CHANGE] '
labels: 'change:normal'
assignees: ''
---

## Change Summary
**Brief description of the change:**


**Change type:** (Select one)
- [ ] Standard (low-risk, pre-approved)
- [ ] Normal (requires approval)
- [ ] Emergency (critical issue)
- [ ] Major (high-risk, full review)

---

## Business Justification
**Why is this change needed?**


**What problem does it solve?**


**What is the business impact if NOT implemented?**


---

## Technical Details

### What is changing?
- [ ] Application code
- [ ] Database schema
- [ ] Configuration
- [ ] Infrastructure
- [ ] Third-party integration
- [ ] Security controls
- [ ] Other: ___________

### Affected systems/components:


### Changes to be made:


---

## Risk Assessment

### Impact on users:
- [ ] No user impact
- [ ] Minor UX change (low risk)
- [ ] Major functionality change (high risk)

### Data risk:
- [ ] No data touched
- [ ] Data read/display only
- [ ] Data write/modification (medium risk)
- [ ] Data migration/deletion (high risk)

### System complexity:
- [ ] Single file change
- [ ] Multiple files/modules
- [ ] Architecture change (high risk)

### Rollback difficulty:
- [ ] Easy (simple code revert)
- [ ] Medium (database migration involved)
- [ ] Difficult (data migration, no easy rollback)

### Dependencies:
- [ ] None
- [ ] Internal dependencies only
- [ ] External dependencies (third-party services)

**Overall risk score:** ___ / 15 (sum of all factors: Low=1, Medium=2, High=3)

**Identified risks:**
1. 
2. 
3. 

---

## Testing Plan

### Pre-deployment testing:
- [ ] Unit tests written/updated
- [ ] Integration tests written/updated
- [ ] Manual testing completed
- [ ] Staging deployment successful
- [ ] Smoke tests passed

### Test cases:
1. 
2. 
3. 

### Testing completed by:
- **Tester name:** 
- **Date:** 
- **Result:** Pass / Fail

---

## Rollback Plan

### How to rollback if something goes wrong:


### Rollback time estimate:


### Data recovery plan (if applicable):


---

## Deployment Plan

### Deployment steps:
1. 
2. 
3. 

### Deployment window:
- **Preferred date/time:** 
- **Estimated duration:** 

### Monitoring plan:
- **Metrics to watch:** 
- **Monitoring duration:** 

### Notification plan:
- [ ] Team notified (24 hours for normal, 1 week for major)
- [ ] Customers notified (if user-facing)
- [ ] Stakeholders notified

---

## Pre-Deployment Checklist

Before deployment, confirm:
- [ ] All approvals obtained
- [ ] All tests passed
- [ ] Staging deployment successful (normal/major changes)
- [ ] Rollback plan documented
- [ ] Backup verified (if database changes)
- [ ] Team available for support
- [ ] Monitoring dashboard ready
- [ ] Change scheduled during approved window

---

## Approval

**Requested by:** @_________  
**Date:** __________

**Reviewed by:** @_________  
**Approved:** Yes / No  
**Date:** __________

---

## Post-Deployment

### Deployment completed:
- **Date/time:** 
- **Deployed by:** 
- **Result:** Success / Failed / Rolled back

### Verification:
- [ ] Application is running
- [ ] No error spikes
- [ ] Key functionality working
- [ ] Performance normal
- [ ] No customer complaints

### Issues encountered:


### Lessons learned:


---

**Document Reference:** See `docs/Change_Management_Policy.md` for full process
