import requests
import json

url = "https://www.workatastartup.com/companies/fetch"

payload = json.dumps({
  "ids": [i for i in range(1000000)]
})
headers = {
  'accept': 'application/json',
  'accept-language': 'en-US,en;q=0.9,hi;q=0.8,zh-TW;q=0.7,zh;q=0.6,ja;q=0.5,zh-CN;q=0.4,de;q=0.3',
  'baggage': 'sentry-environment=production,sentry-release=46fb02abf7945cecd0857f18d559448e3fc6fe0a,sentry-public_key=788c28f2d583d3ada82afc01f294c559,sentry-trace_id=291ce7a1f0754c358a56acf060729613,sentry-org_id=4506690008121344,sentry-sampled=false,sentry-sample_rand=0.9570337569977201,sentry-sample_rate=0.05',
  'cache-control': 'no-cache',
  'content-type': 'application/json',
  'origin': 'https://www.workatastartup.com',
  'pragma': 'no-cache',
  'priority': 'u=1, i',
  'referer': 'https://www.workatastartup.com/companies?demographic=any&hasEquity=any&hasSalary=any&industry=any&interviewProcess=any&jobType=any&layout=list-compact&locations=CA%2C%20US&role=product&sortBy=created_desc&tab=any&usVisaNotRequired=true',
  'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'sentry-trace': '291ce7a1f0754c358a56acf060729613-b08ad3378c13772c-0',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
  'x-csrf-token': 'njUCXiPBSIiRm0HrQTvVNdVm6jKeHblZyyWRvSeiGwzVNsgUFL2-X1LFABWUuy8WaM5AiBlVDpviKyIMV_HVpg',
  'x-requested-with': 'XMLHttpRequest',
  'x-tab-id': 'bbf15ad3-99a7-4226-823e-b34fc67d3507',
  'Cookie': 'f3k2kqs7xc=b5131c4afcdf34474832fd426716f76d; _bf_session_exists=eyJfcmFpbHMiOnsibWVzc2FnZSI6ImRISjFaUT09IiwiZXhwIjpudWxsLCJwdXIiOiJjb29raWUuX2JmX3Nlc3Npb25fZXhpc3RzIn19--c09bf3da17accf4c53e92f910eef613c6f99527b; _sso.key=dK8j5UQFXoTSwDrO-nZbvnMZcLjZi3Nt; waasInboxSortBy=newest; ph_phc_kqzJJG8aN5nevL0k1oW4Z8iAGswsxBnsWqIBcOuxjah_posthog=%7B%22%24device_id%22%3A%22cabc2741-3e9c-4554-b70a-723a80a6aecc%22%2C%22distinct_id%22%3A%22f09ce9e4-f476-4cf7-b227-cbdb5960fc91%22%2C%22%24sesid%22%3A%5B1779927194913%2C%22019e6bde-9384-7a02-b9f5-b55c4f5950e4%22%2C1779926209410%5D%2C%22%24epp%22%3Atrue%2C%22%24initial_person_info%22%3A%7B%22r%22%3A%22https%3A%2F%2Fwww.ycombinator.com%2F%22%2C%22u%22%3A%22https%3A%2F%2Fwww.workatastartup.com%2Fjobs%2F78885%22%7D%2C%22%24user_state%22%3A%22identified%22%7D; XSRF-TOKEN=qVjCImep6wCnYeA3aL3PrPh326yzeUB-iA1lOEjki3viWwhoUNUd12Q_ocm9PTWPRd9xFjQx97yhA9aJOLdF0Q; _bf_session_key=EkpLL0wA1P%2B3JQPQw5izYONnoF%2B7142ZbaVx0D0eSVrrWGPQZ7k3zFzalvmIdpKCo9O7keQEs4YlfGWZOo43LlfaIP5OvBrDZrH8dSdaOOBoM2sUKBAtg2Bf94ihQxygdvGygD0f%2BjHhgD68nn8mdznDi2rhVaqtrgm15Ju%2BcNWyDisPYRS9s4Wv33hHX73dO%2BZVs54%2BrVGHyIfUvMd3fVUduRmeicePXhOX%2FOhLooPrQeYk8ttWnaxRRVlwBUHIBp5KrG5MFuYxDsgVzpXRv8hzPL8xEbA%3D--uQGBmS2cPaegHX9h--TuOPsy%2FvtrNRbebJdWvKyA%3D%3D; XSRF-TOKEN=4TtnoQceuHVXLuKJYkWK54wnqbSQhCJOx5byNrSdEoyqOK3rMGJOopRwo3e3xXDEMY8DDhfMlYzumEGHxM7cJg; _bf_session_key=AbRkWU8zNI36MXVtZYv%2FyKq5lifREKdSe31V25jmzgIyrJikgoWuJz04c566OvXlj8ugqorwLgCDD9W6HdvPix2%2Fl1tEpOrLEkg3VzACxHYMLW0GVastu%2BbmXGFhoDoq6AmdnXwKkfHs7QJ4fA3xqzPgQ42fknGyOZHNC0SuHzUfhJ%2FivdoxoQn1B7LcqYbKqilylcGClTkx4yYNg39QVug56HrrVobtYO0jB83rKD%2FNzQu6TkIfHSYXvgc6ZrxjRpJFPKDq8hTATdwvF5l%2ByLX74IoY6L0%3D--%2Bl%2BbHb5t7XDygkbH--4eHtvlSTAUDFaFFnM1KwHg%3D%3D'
}

#response = requests.request("POST", url, headers=headers, data=payload)
#with open("jobs.json", "w", encoding="utf-8") as f:
 #   f.write(response.text)
companies=json.load(open('jobs.json', 'r', encoding="utf-8"))['companies']
recommended=json.load(open('jobs.json', 'r', encoding="utf-8"))['recommendedJobIds']
matched=[]
for recom in recommended:
    for company in companies:
        for job in company['jobs']:
            if recom==job['id']:
                matched.append(job)
json.dump(matched, open('matched.json', 'w', encoding="utf-8"), ensure_ascii=False, indent=4)