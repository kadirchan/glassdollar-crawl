from celery import Celery, group
from celery.result import AsyncResult, allow_join_result
import requests
import spacy
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

app = Celery('celery_app', broker='amqp://guest:guest@rabbitmq:5672//', backend='rpc://')


base_query = """
    query {{
      corporates(
        filters:{{
          hq_city: [],
          industry: []
        }},
        page: {page},
        sortBy: ""
      ){{
        rows {{
          id,
          name,
          description,
          logo_url,
          website_url,
          linkedin_url,
          twitter_url,
          industry,
          hq_city,
          hq_country,
          startup_friendly_badge,
          startup_partners_count
        }},
        count
      }}
    }}
    """

get_corporate_from_id = """
    query {{
      corporate(id: "{id}") {{
        id,
        name,
        description,
        logo_url,
        website_url,
        linkedin_url,
        twitter_url,
        hq_city,
        hq_country,
        startup_partners_count,
        startup_partners
        {{
          master_startup_id
          company_name
          website
          city
          country
          logo
        }},
        startup_themes
      }}
    }}
    """
graphql_endpoint = "https://ranking.glassdollar.com/graphql"

headers = {
    "Content-Type": "application/json",
}

class Corporate:
    def __init__(self, data):
        self.id = data.get("id")
        self.name = data.get("name")
        self.description = data.get("description")
        self.logo_url = data.get("logo_url")
        self.website_url = data.get("website_url")
        self.linkedin_url = data.get("linkedin_url")
        self.twitter_url = data.get("twitter_url")
        self.hq_city = data.get("hq_city")
        self.hq_country = data.get("hq_country")
        self.startup_partners_count = data.get("startup_partners_count")
        self.startup_themes = data.get("startup_themes")
        self.startup_partners = [
            StartupPartner(startup_data)
            for startup_data in data.get("startup_partners", [])
        ]
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "logo_url": self.logo_url,
            "website_url": self.website_url,
            "linkedin_url": self.linkedin_url,
            "twitter_url": self.twitter_url,
            "hq_city": self.hq_city,
            "hq_country": self.hq_country,
            "startup_partners_count": self.startup_partners_count,
            "startup_themes": self.startup_themes,
            "startup_partners": [partner.to_dict() for partner in self.startup_partners]
        }

class StartupPartner:
    def __init__(self, data):
        self.master_startup_id = data.get("master_startup_id")
        self.company_name = data.get("company_name")
        self.website = data.get("website")
        self.city = data.get("city")
        self.country = data.get("country")
        self.logo = data.get("logo")
    def to_dict(self):
        return {
            "master_startup_id": self.master_startup_id,
            "company_name": self.company_name,
            "website": self.website,
            "city": self.city,
            "country": self.country,
            "logo": self.logo
        }

@app.task
def get_corporates():

    corporate_ids = get_corporate_ids()

    corporate_details_tasks = []

    for corporate_id in corporate_ids:
        corporate_details_tasks.append(get_corporate_details.s(corporate_id))

    corporate_details_group = group(corporate_details_tasks)
    corporate_details_group_result = corporate_details_group.apply_async()

    with allow_join_result():
        corporate_details = corporate_details_group_result.get()

    clusters = get_clusters(corporate_details)
    response = {
        "result": corporate_details,
        "clusters": clusters
    }

    return response
@app.task
def get_corporate_details(corporate_id):
    request_payload = {
        "query": get_corporate_from_id.format(id=corporate_id),
    }
    response = requests.post(graphql_endpoint, json=request_payload, headers=headers)
    data = response.json()
    data = data["data"]["corporate"]
    corporate = Corporate(data)
    return corporate.to_dict()

@app.task
def get_corporate_count():
    request_payload = {
        "query": """query { getCorporateCount }"""
    }
    response = requests.post(graphql_endpoint, json=request_payload, headers=headers)
    data = response.json()
    return data["data"]["getCorporateCount"]
    
@app.task
def get_corporate_ids():
    corporate_ids = set()
    corporate_count = get_corporate_count()
    page_number = 1
    while (page_number - 1) * 32 < corporate_count:
        request_payload = {
            "query": base_query.format(page=page_number),
        }
        response = requests.post(graphql_endpoint, json=request_payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for corporate_data in data["data"]["corporates"]["rows"]:
                corporate_ids.add(corporate_data["id"])
        else:
            raise Exception("Error when fetching corporate ids")
        
        page_number += 1

    return corporate_ids

def get_result(task_id):
    return AsyncResult(task_id, app=app)

    
@app.task
def get_clusters(corporates):
    descriptions = [corporates['description'] for corporates in corporates ]
    nlp = spacy.load('en_core_web_md')

    def get_vector(text):
        return nlp(text).vector

    company_vectors = [get_vector(description) for description in descriptions]

    similarity_matrix = cosine_similarity(company_vectors)

    kmeans = KMeans(n_clusters=5)
    clusters = kmeans.fit_predict(similarity_matrix)

    clustered_companies = [[] for i in range(5)]

    for i in range(len(clusters)):
        clustered_companies[clusters[i]].append(corporates[i]['name'])

    return clustered_companies